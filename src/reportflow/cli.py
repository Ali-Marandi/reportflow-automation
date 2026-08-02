import sys
import logging
import click
from pathlib import Path
from .pipeline import run_pipeline
from .scheduler import ReportFlowScheduler

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

@click.command()
@click.argument('config', type=click.Path(exists=True))
@click.option('--output', '-o', default='reportflow-output', help='Output directory for reports')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(config, output, verbose):
    """ReportFlow: Professional Financial Reporting Automation."""
    setup_logging(verbose)
    logger = logging.getLogger("reportflow")
    
    logger.info("Starting ReportFlow pipeline...")
    try:
        results = run_pipeline(config, output)
        logger.info("Pipeline completed successfully.")
        for fmt, path in results.items():
            click.echo(f"Generated {fmt.upper()} report: {path}")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if verbose:
            logger.exception(e)
        sys.exit(1)

@click.command("schedule")
@click.argument("config", type=click.Path(exists=True))
@click.option("--output", "-o", default="reportflow-output", help="Output directory for reports")
@click.option("--cron", default=None, help="Cron expression (5 fields, UTC), e.g. '0 8 * * 1-5'")
@click.option("--interval", default=None, type=int, help="Interval in seconds between runs")
@click.option("--heartbeat-path", default=None, help="Path for heartbeat JSON file")
@click.option("--heartbeat-interval", default=10, type=float, help="Seconds between heartbeat writes")
@click.option("--db-path", default=None, help="SQLite path for persistent job store")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def schedule_cmd(config, output, cron, interval, heartbeat_path, heartbeat_interval, db_path, verbose):
    """Run ReportFlow as a persistent scheduled daemon with heartbeat support.

    Examples:

    \b
      # Every weekday at 08:00 UTC
      reportflow schedule config.json -o output/ --cron '0 8 * * 1-5'

    \b
      # Every 30 minutes
      reportflow schedule config.json -o output/ --interval 1800
    """
    setup_logging(verbose)
    logger = logging.getLogger("reportflow")

    if not cron and not interval:
        raise click.UsageError("Provide either --cron or --interval.")
    if cron and interval:
        raise click.UsageError("Use only one of --cron or --interval.")

    kwargs = {}
    if heartbeat_path:
        kwargs["heartbeat_path"] = Path(heartbeat_path)
    if db_path:
        kwargs["db_path"] = Path(db_path)
    kwargs["heartbeat_interval"] = heartbeat_interval

    scheduler = ReportFlowScheduler(**kwargs)

    if cron:
        job_id = scheduler.add_cron_job(config, output, cron)
    else:
        job_id = scheduler.add_interval_job(config, output, seconds=interval)

    logger.info("Job '%s' registered. Starting scheduler daemon…", job_id)
    scheduler.run_forever()


@click.group()
def cli():
    """ReportFlow: Professional Financial Reporting Automation."""


cli.add_command(main, name="run")
cli.add_command(schedule_cmd, name="schedule")


if __name__ == "__main__":
    cli()
