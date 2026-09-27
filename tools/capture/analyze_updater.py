"""E1-alt: scan vendor updater binaries for ZD2 protocol signatures.

Answers, without touching the device, which payloads the updater sends and
whether filesystem write paths exist. Findings are recorded in
docs/research/2026-09-27-e1alt-updater-analysis.md.
"""

import argparse
import json
from pathlib import Path

SIGNATURES = {
    "pcmode_on_52": bytes([0x52, 0x00, 0x6E, 0x52]),
    "pcmode_off_53": bytes([0x52, 0x00, 0x6E, 0x53]),
    "enter_update_mode_01": bytes([0x52, 0x00, 0x6E, 0x01]),
    "patch_upload_opcode_45": bytes([0x52, 0x00, 0x6E, 0x45]),
    "patch_download_opcode_46": bytes([0x52, 0x00, 0x6E, 0x46]),
    "file_open_write_60_20_01": bytes([0x60, 0x20, 0x01]),
    "file_open_read_60_20_02": bytes([0x60, 0x20, 0x02]),
    "file_open_other_60_20_00": bytes([0x60, 0x20, 0x00]),
    "file_open_other_60_20_03": bytes([0x60, 0x20, 0x03]),
    "file_read_block_60_22": bytes([0x60, 0x22]),
    "file_upload_block_60_23": bytes([0x60, 0x23]),
    "file_delete_60_24": bytes([0x60, 0x24]),
    "file_close_60_21": bytes([0x60, 0x21]),
    "file_list_60_25": bytes([0x60, 0x25]),
    "file_list_next_60_26": bytes([0x60, 0x26]),
    "file_api_60_27": bytes([0x60, 0x27]),
    "file_api_60_09": bytes([0x60, 0x09]),
    "file_ack_60_05": bytes([0x60, 0x05]),
}

STRINGS = [
    "FS.bin",
    "Main.bin",
    "ROM.bin",
    "Preset.bin",
    "MAIN_INFO.bin",
    "GUARDZDL.ZT2",
    "FLST_SEQ.ZT2",
    "G1 IV",
    "G1X IV",
]


def scan(data: bytes, exclude_blobs=()) -> dict:
    excludes = [bytes(blob) for blob in exclude_blobs]
    return {
        "size": len(data),
        "signatures": {
            name: data.count(pattern) - sum(blob.count(pattern) for blob in excludes)
            for name, pattern in SIGNATURES.items()
        },
        "strings": {
            text: data.count(text.encode("ascii"))
            - sum(blob.count(text.encode("ascii")) for blob in excludes)
            for text in STRINGS
        },
    }


def scan_path(path: Path, exclude_paths=()) -> dict:
    exclude_paths = [Path(item) for item in exclude_paths]
    report = scan(Path(path).read_bytes(), [item.read_bytes() for item in exclude_paths])
    report["path"] = str(path)
    report["excluded"] = [str(item) for item in exclude_paths]
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.capture.analyze_updater")
    parser.add_argument("binaries", nargs="+", type=Path)
    parser.add_argument("--exclude", action="append", default=[], type=Path,
                        help="payload file whose bytes are embedded in the binary; subtracted from counts")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    for path in args.binaries:
        report = scan_path(path, args.exclude)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"== {report['path']} ({report['size']} bytes)")
            for name, count in sorted(report["signatures"].items()):
                print(f"  {name:28s} {count}")
            for text, count in sorted(report["strings"].items()):
                print(f"  str {text:24s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
