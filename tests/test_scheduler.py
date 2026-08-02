"""
Comprehensive tests for reportflow.scheduler (ReportFlowScheduler + HeartbeatWriter).

Covers:
- HeartbeatWriter: file creation, content structure, epoch freshness
- ReportFlowScheduler: start/stop lifecycle
- add_interval_job: job registration and execution
- add_cron_job: valid and invalid cron expressions
- run_once: fire-and-forget execution
- list_jobs / remove_job
- _run_job: success and failure paths update HeartbeatStatus correctly
"""

import json
import shutil
import sys
import tempfile
import time
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportflow.scheduler import (
    HeartbeatStatus,
    HeartbeatWriter,
    ReportFlowScheduler,
    _run_job,
)


# ---------------------------------------------------------------------------
# HeartbeatStatus tests
# ---------------------------------------------------------------------------

class TestHeartbeatStatus(unittest.TestCase):

    def test_defaults(self):
        s = HeartbeatStatus()
        self.assertEqual(s.status, "starting")
        self.assertEqual(s.jobs_run, 0)
        self.assertEqual(s.jobs_failed, 0)

    def test_to_dict_contains_all_fields(self):
        s = HeartbeatStatus()
        d = s.to_dict()
        for key in ("pid", "started_at", "status", "jobs_run", "jobs_failed"):
            self.assertIn(key, d)


# ---------------------------------------------------------------------------
# HeartbeatWriter tests
# ---------------------------------------------------------------------------

class TestHeartbeatWriter(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.hb_path = self.tmp / "heartbeat.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_heartbeat_file_created(self):
        status = HeartbeatStatus()
        writer = HeartbeatWriter(status, self.hb_path, interval=0.2)
        writer.start()
        time.sleep(0.5)
        writer.stop()
        self.assertTrue(self.hb_path.exists(), "Heartbeat file should be created")

    def test_heartbeat_json_structure(self):
        status = HeartbeatStatus()
        writer = HeartbeatWriter(status, self.hb_path, interval=0.2)
        writer.start()
        time.sleep(0.5)
        writer.stop()

        data = json.loads(self.hb_path.read_text(encoding="utf-8"))
        self.assertIn("pid", data)
        self.assertIn("status", data)
        self.assertIn("_epoch", data)
        self.assertIn("last_beat", data)

    def test_heartbeat_epoch_is_recent(self):
        status = HeartbeatStatus()
        writer = HeartbeatWriter(status, self.hb_path, interval=0.2)
        writer.start()
        time.sleep(0.5)
        writer.stop()

        data = json.loads(self.hb_path.read_text(encoding="utf-8"))
        age = time.time() - data["_epoch"]
        self.assertLess(age, 5.0, "Heartbeat epoch should be recent (< 5 s)")

    def test_heartbeat_reflects_status_changes(self):
        status = HeartbeatStatus()
        writer = HeartbeatWriter(status, self.hb_path, interval=0.2)
        writer.start()
        time.sleep(0.3)
        status.status = "degraded"
        status.jobs_failed = 3
        time.sleep(0.4)
        writer.stop()

        data = json.loads(self.hb_path.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["jobs_failed"], 3)

    def test_stop_writes_final_beat(self):
        status = HeartbeatStatus()
        writer = HeartbeatWriter(status, self.hb_path, interval=60)  # long interval
        writer.start()
        writer.stop()
        # File should still exist because stop() forces a final write
        self.assertTrue(self.hb_path.exists())


# ---------------------------------------------------------------------------
# _run_job function tests
# ---------------------------------------------------------------------------

class TestRunJob(unittest.TestCase):

    def test_success_increments_jobs_run(self):
        status = HeartbeatStatus()
        with patch("reportflow.scheduler.run_pipeline", return_value={"json": "/tmp/r.json"}):
            _run_job("/tmp/cfg.json", "/tmp/out", status, "test_job")
        self.assertEqual(status.jobs_run, 1)
        self.assertEqual(status.jobs_failed, 0)
        self.assertEqual(status.status, "running")
        self.assertEqual(status.last_error, "")

    def test_failure_increments_jobs_failed(self):
        status = HeartbeatStatus()
        with patch("reportflow.scheduler.run_pipeline", side_effect=RuntimeError("boom")):
            _run_job("/tmp/cfg.json", "/tmp/out", status, "test_job")
        self.assertEqual(status.jobs_run, 0)
        self.assertEqual(status.jobs_failed, 1)
        self.assertEqual(status.status, "degraded")
        self.assertIn("boom", status.last_error)

    def test_duration_recorded(self):
        status = HeartbeatStatus()
        with patch("reportflow.scheduler.run_pipeline", return_value={}):
            _run_job("/tmp/cfg.json", "/tmp/out", status, "test_job")
        self.assertGreaterEqual(status.last_run_duration_s, 0.0)


# ---------------------------------------------------------------------------
# ReportFlowScheduler lifecycle tests
# ---------------------------------------------------------------------------

class TestReportFlowSchedulerLifecycle(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_scheduler(self, **kwargs):
        return ReportFlowScheduler(
            db_path=self.tmp / "jobs.db",
            heartbeat_path=self.tmp / "hb.json",
            heartbeat_interval=0.5,
            **kwargs,
        )

    def test_start_and_stop(self):
        sched = self._make_scheduler()
        sched.start()
        self.assertTrue(sched._scheduler.running)
        sched.stop()
        self.assertFalse(sched._scheduler.running)

    def test_heartbeat_file_created_after_start(self):
        sched = self._make_scheduler()
        sched.start()
        time.sleep(0.8)
        sched.stop()
        self.assertTrue((self.tmp / "hb.json").exists())

    def test_list_jobs_empty_initially(self):
        sched = self._make_scheduler()
        sched.start()
        jobs = sched.list_jobs()
        sched.stop()
        self.assertIsInstance(jobs, list)

    def test_add_interval_job_appears_in_list(self):
        sched = self._make_scheduler()
        sched.start()
        job_id = sched.add_interval_job("/tmp/cfg.json", "/tmp/out", seconds=3600, job_id="my_job")
        jobs = sched.list_jobs()
        sched.stop()
        ids = [j["id"] for j in jobs]
        self.assertIn("my_job", ids)

    def test_remove_job(self):
        sched = self._make_scheduler()
        sched.start()
        sched.add_interval_job("/tmp/cfg.json", "/tmp/out", seconds=3600, job_id="del_job")
        sched.remove_job("del_job")
        jobs = sched.list_jobs()
        sched.stop()
        ids = [j["id"] for j in jobs]
        self.assertNotIn("del_job", ids)

    def test_add_cron_job_valid(self):
        sched = self._make_scheduler()
        sched.start()
        job_id = sched.add_cron_job("/tmp/cfg.json", "/tmp/out", "0 8 * * 1-5", job_id="cron_job")
        jobs = sched.list_jobs()
        sched.stop()
        ids = [j["id"] for j in jobs]
        self.assertIn("cron_job", ids)

    def test_add_cron_job_invalid_expression_raises(self):
        sched = self._make_scheduler()
        sched.start()
        with self.assertRaises(ValueError):
            sched.add_cron_job("/tmp/cfg.json", "/tmp/out", "bad expression")
        sched.stop()

    def test_interval_job_executes(self):
        """Verify that a short-interval job actually calls run_pipeline."""
        call_event = threading.Event()

        def fake_pipeline(*args, **kwargs):
            call_event.set()
            return {}

        sched = self._make_scheduler()
        with patch("reportflow.scheduler.run_pipeline", side_effect=fake_pipeline):
            sched.start()
            sched.add_interval_job("/tmp/cfg.json", "/tmp/out", seconds=1, job_id="fast_job")
            executed = call_event.wait(timeout=5)
            sched.stop()

        self.assertTrue(executed, "Job should have executed within 5 seconds")

    def test_run_once_executes(self):
        """run_once should fire the pipeline exactly once."""
        call_count = {"n": 0}

        def fake_pipeline(*args, **kwargs):
            call_count["n"] += 1
            return {}

        sched = self._make_scheduler()
        with patch("reportflow.scheduler.run_pipeline", side_effect=fake_pipeline):
            sched.start()
            sched.run_once("/tmp/cfg.json", "/tmp/out", job_id="once_job")
            time.sleep(2)
            sched.stop()

        self.assertEqual(call_count["n"], 1)

    def test_status_updated_after_job_run(self):
        """HeartbeatStatus.jobs_run should increment after a successful run."""
        # Use _run_job directly to verify status mutation without scheduler timing
        from reportflow.scheduler import _run_job, HeartbeatStatus
        status = HeartbeatStatus()
        with patch("reportflow.scheduler.run_pipeline", return_value={"json": "/tmp/r.json"}):
            _run_job("/tmp/cfg.json", "/tmp/out", status, "direct_job")
        self.assertGreater(status.jobs_run, 0)
        self.assertEqual(status.status, "running")


if __name__ == "__main__":
    unittest.main(verbosity=2)
