from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a reproducible multi-source report")
    parser.add_argument("config")
    parser.add_argument("--output", default="reportflow-output")
    args = parser.parse_args(argv)
    for kind, path in run_pipeline(args.config, args.output).items():
        print(f"{kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
