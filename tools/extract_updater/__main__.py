"""CLI: python -m tools.extract_updater {fetch,extract,verify}"""

import argparse
from pathlib import Path

from .pipeline import extract_all, fetch_all, verify_all
from .utils import sha256_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.extract_updater")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="download the pristine official packages")
    sub.add_parser("extract", help="extract canonical bins + SHA256SUMS")
    sub.add_parser("verify", help="verify extracted artifacts against known-good hashes")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    official = repo / "firmware" / "official"
    extracted = repo / "firmware" / "extracted"
    work = repo / ".work" / "p0"

    if args.command == "fetch":
        for key, path in fetch_all(official).items():
            print(f"{key}: {path} {sha256_file(path)}")
    elif args.command == "extract":
        bins = extract_all(official, extracted, work)
        for name, path in sorted(bins.items()):
            print(f"{name}: {path.stat().st_size} bytes {sha256_file(path)}")
        print(f"wrote {extracted / 'SHA256SUMS'}")
    elif args.command == "verify":
        verify_all(extracted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
