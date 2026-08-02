import sys
import logging
import click
from pathlib import Path
from .pipeline import run_pipeline

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

if __name__ == "__main__":
    main()
