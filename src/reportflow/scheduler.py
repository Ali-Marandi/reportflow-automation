"""
ReportFlow Scheduler — real-time scheduling with heartbeat integration.

Features
--------
* APScheduler-based cron / interval / one-shot triggers
* Thread-safe heartbeat that writes a JSON status file every ``heartbeat_interval``
  seconds so external monitors (systemd, Docker health-check, Kubernetes liveness
  probe) can verify the daemon is alive.
* Graceful shutdown on SIGINT / SIGTERM.
* Persistent job store (SQLite) so jobs survive process restarts.
* Structured logging with per-run durations and error counts.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from .pipeline import run_pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

@dataclass
class HeartbeatStatus:
    """Serialisable snapshot of scheduler health."""

    pid: int = field(default_factory=os.getpid)
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_beat: str = ""
    status: str = "starting"          # starting | running | degraded | stopped
    jobs_run: int = 0
    jobs_failed: int = 0
    last_run_at: str = ""
    last_run_duration_s: float = 0.0
    last_error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class HeartbeatWriter:
    """
    Writes a JSON heartbeat file at a fixed interval in a daemon thread.

    External tools can ``cat heartbeat.json`` or mount it as a Docker
    health-check target::

        HEALTHCHECK --interval=30s --timeout=5s \\
            CMD python - <<'EOF'
        import json, sys, time
        d = json.load(open('/tmp/reportflow_heartbeat.json'))
        age = time.time() - d['_epoch']
        sys.exit(0 if age < 60 else 1)
        EOF
    """

    def __init__(
        self,
        status: HeartbeatStatus,
        heartbeat_path: Path,
        interval: float = 10.0,
    ) -> None:
        self._status = status
        self._path = heartbeat_path
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._loop, name="heartbeat-writer", daemon=True
        )

    def start(self) -> None:
        self._thread.start()
        logger.info("Heartbeat writer started → %s (every %.0fs)", self._path, self._interval)

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=self._interval + 2)

    def _loop(self) -> None:
        while not self._stop_event.wait(self._interval):
            self._write()
        self._write()  # final beat on shutdown

    def _write(self) -> None:
        now = datetime.now(timezone.utc)
        self._status.last_beat = now.isoformat()
        payload = self._status.to_dict()
        payload["_epoch"] = now.timestamp()
        try:
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self._path)
        except OSError as exc:
            logger.warning("Heartbeat write failed: %s", exc)


# ---------------------------------------------------------------------------
# Job wrapper
# ---------------------------------------------------------------------------

def _run_job(
    config_path: str,
    output_dir: str,
    status: HeartbeatStatus,
    job_id: str,
) -> None:
    """Execute one pipeline run and update the shared status object."""
    t0 = time.monotonic()
    logger.info("[%s] Pipeline run starting — config=%s output=%s", job_id, config_path, output_dir)
    try:
        results = run_pipeline(config_path, output_dir)
        elapsed = time.monotonic() - t0
        status.jobs_run += 1
        status.last_run_at = datetime.now(timezone.utc).isoformat()
        status.last_run_duration_s = round(elapsed, 3)
        status.last_error = ""
        status.status = "running"
        logger.info(
            "[%s] Pipeline completed in %.2fs → %s",
            job_id,
            elapsed,
            {k: str(v) for k, v in results.items()},
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - t0
        status.jobs_failed += 1
        status.last_run_at = datetime.now(timezone.utc).isoformat()
        status.last_run_duration_s = round(elapsed, 3)
        status.last_error = str(exc)
        status.status = "degraded"
        logger.error("[%s] Pipeline failed after %.2fs: %s", job_id, elapsed, exc, exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class ReportFlowScheduler:
    """
    High-level scheduler that wraps APScheduler with heartbeat support.

    Parameters
    ----------
    db_path:
        SQLite file for persistent job storage.  Defaults to
        ``~/.reportflow/jobs.db``.
    heartbeat_path:
        Path for the JSON heartbeat file.  Defaults to
        ``/tmp/reportflow_heartbeat.json``.
    heartbeat_interval:
        Seconds between heartbeat file updates.
    max_workers:
        Thread-pool size for concurrent job execution.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        heartbeat_path: Optional[Path] = None,
        heartbeat_interval: float = 10.0,
        max_workers: int = 4,
    ) -> None:
        if db_path is None:
            db_path = Path.home() / ".reportflow" / "jobs.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        if heartbeat_path is None:
            heartbeat_path = Path("/tmp/reportflow_heartbeat.json")

        jobstores = {
            "default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}")
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=max_workers)
        }
        job_defaults = {
            "coalesce": True,       # skip missed runs instead of piling up
            "max_instances": 1,     # never run the same job twice simultaneously
            "misfire_grace_time": 60,
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )
        self._status = HeartbeatStatus()
        self._heartbeat = HeartbeatWriter(
            self._status, heartbeat_path, heartbeat_interval
        )
        self._heartbeat_path = heartbeat_path
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_cron_job(
        self,
        config_path: str | Path,
        output_dir: str | Path,
        cron_expression: str,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Schedule a pipeline run using a cron expression.

        Parameters
        ----------
        cron_expression:
            Standard 5-field cron string, e.g. ``"0 8 * * 1-5"`` for
            weekdays at 08:00 UTC.

        Returns
        -------
        str
            The APScheduler job ID.
        """
        fields = cron_expression.strip().split()
        if len(fields) != 5:
            raise ValueError(
                f"cron_expression must have exactly 5 fields, got {len(fields)}: {cron_expression!r}"
            )
        minute, hour, day, month, day_of_week = fields
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone="UTC",
        )
        job_id = job_id or f"cron_{Path(config_path).stem}"
        self._add_job(config_path, output_dir, trigger, job_id)
        logger.info("Cron job registered: %s  schedule=%r", job_id, cron_expression)
        return job_id

    def add_interval_job(
        self,
        config_path: str | Path,
        output_dir: str | Path,
        seconds: int = 3600,
        job_id: Optional[str] = None,
    ) -> str:
        """
        Schedule a pipeline run at a fixed interval.

        Parameters
        ----------
        seconds:
            Interval in seconds between runs (default: 3600 = 1 hour).
        """
        trigger = IntervalTrigger(seconds=seconds, timezone="UTC")
        job_id = job_id or f"interval_{Path(config_path).stem}"
        self._add_job(config_path, output_dir, trigger, job_id)
        logger.info("Interval job registered: %s  every=%ds", job_id, seconds)
        return job_id

    def run_once(
        self,
        config_path: str | Path,
        output_dir: str | Path,
        job_id: Optional[str] = None,
    ) -> str:
        """Run the pipeline exactly once (fire-and-forget via scheduler thread)."""
        from apscheduler.triggers.date import DateTrigger

        trigger = DateTrigger(run_date=datetime.now(timezone.utc), timezone="UTC")
        job_id = job_id or f"once_{Path(config_path).stem}"
        self._add_job(config_path, output_dir, trigger, job_id)
        logger.info("One-shot job registered: %s", job_id)
        return job_id

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job by ID."""
        try:
            self._scheduler.remove_job(job_id)
            logger.info("Job removed: %s", job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not remove job %s: %s", job_id, exc)

    def list_jobs(self) -> list[dict]:
        """Return a list of dicts describing all scheduled jobs."""
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs

    def start(self) -> None:
        """Start the scheduler and heartbeat writer."""
        self._scheduler.start()
        self._status.status = "running"
        self._heartbeat.start()
        logger.info(
            "ReportFlowScheduler started — heartbeat → %s", self._heartbeat_path
        )

    def stop(self) -> None:
        """Gracefully shut down the scheduler and heartbeat writer."""
        logger.info("Shutting down ReportFlowScheduler…")
        self._status.status = "stopped"
        self._scheduler.shutdown(wait=True)
        self._heartbeat.stop()
        self._stop_event.set()
        logger.info("ReportFlowScheduler stopped.")

    def run_forever(self) -> None:
        """
        Block the calling thread until SIGINT or SIGTERM is received.

        Intended for use as a long-running daemon process::

            scheduler = ReportFlowScheduler()
            scheduler.add_cron_job("config.json", "output/", "0 * * * *")
            scheduler.start()
            scheduler.run_forever()
        """
        self.start()

        def _handle_signal(signum, frame):  # noqa: ANN001
            logger.info("Signal %s received — initiating shutdown…", signum)
            self.stop()
            self._stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        logger.info("Scheduler running. Press Ctrl-C or send SIGTERM to stop.")
        self._stop_event.wait()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_job(
        self,
        config_path: str | Path,
        output_dir: str | Path,
        trigger,
        job_id: str,
    ) -> None:
        self._scheduler.add_job(
            _run_job,
            trigger=trigger,
            id=job_id,
            name=job_id,
            args=[str(config_path), str(output_dir), self._status, job_id],
            replace_existing=True,
        )
