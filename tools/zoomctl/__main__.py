"""CLI: python -m tools.zoomctl {ports,identity,backup}"""

import argparse
import sys
from pathlib import Path

from .backup import run_backup
from .pedal import PedalError, ZoomPedal
from .transport import MidoTransport, TransportError


def _open_pedal() -> ZoomPedal:
    ports = MidoTransport.find_zoom_ports()
    if ports is None:
        sys.exit("No ZOOM G Series MIDI ports found; is the pedal connected?")
    return ZoomPedal(MidoTransport(*ports))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.zoomctl")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ports", help="list ZOOM MIDI ports")
    sub.add_parser("identity", help="query pedal identity")
    backup = sub.add_parser("backup", help="read-only backup of patches and filesystem")
    backup.add_argument("--out", default=None, help="artifact dir (default: backups/)")
    backup.add_argument("--manifests", default=None, help="manifest dir (default: backups/manifests)")
    backup.add_argument("--fs-oracle", default=None, help="FS.bin path (default: firmware/extracted/FS.bin)")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]

    if args.command == "ports":
        import mido

        for kind, names in (("in", mido.get_input_names()), ("out", mido.get_output_names())):
            for name in names:
                print(f"{kind}: {name}")
        return 0

    if args.command == "identity":
        pedal = _open_pedal()
        try:
            identity = pedal.identity()
        except (PedalError, TransportError) as error:
            sys.exit(f"error: {error}")
        finally:
            pedal.transport.close()
        for key in ("model", "model_bytes", "firmware", "reply_hex"):
            print(f"{key}: {identity[key]}")
        return 0

    if args.command == "backup":
        pedal = _open_pedal()
        oracle = Path(args.fs_oracle) if args.fs_oracle else repo / "firmware" / "extracted" / "FS.bin"
        try:
            result = run_backup(
                pedal,
                out_dir=Path(args.out) if args.out else repo / "backups",
                manifests_dir=Path(args.manifests) if args.manifests else repo / "backups" / "manifests",
                oracle_path=oracle,
            )
        except (PedalError, TransportError) as error:
            sys.exit(f"error: {error}")
        finally:
            pedal.transport.close()
        m = result.manifest
        print(f"identity: {m['identity']['model']} firmware {m['identity']['firmware']}")
        print(f"patches: {len(m['patches'])}")
        print(f"files: {len(m['fs']['files'])}")
        print(f"oracle: device_only={m['oracle']['device_only']} oracle_only={m['oracle']['oracle_only']}")
        print(f"artifacts: {result.artifact_dir}")
        print(f"manifest: {result.manifest_path}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
