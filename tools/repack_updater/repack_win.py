"""E5: replace PE resource payloads inside the Windows updater EXE.

Same-size payloads are patched in place at the resource data offsets reported
by pefile, preserving every other byte of the EXE. Payload size changes are
rejected (recorded as a limitation; the Mac .app path or a full PE resource
rewriter would be needed for size-changing edits).
"""

import argparse
import hashlib
from pathlib import Path

import pefile

BIN_RESOURCE_IDS = {
    142: "ROM.bin",
    129: "Main.bin",
    136: "FS.bin",
    139: "MAIN_INFO.bin",
    133: "Preset.bin",
}


def patch_bytes(buffer: bytearray, offset: int, data: bytes) -> bytearray:
    result = bytearray(buffer)
    result[offset:offset + len(data)] = data
    return result


def find_resource_offset(pe: pefile.PE, resource_id: int) -> tuple[int, int]:
    for type_entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        type_name = str(type_entry.name) if type_entry.name is not None else None
        if type_name != "BIN" and getattr(type_entry, "id", None) != 10:
            continue
        for name_entry in type_entry.directory.entries:
            if name_entry.id != resource_id:
                continue
            data_entry = name_entry.directory.entries[0].data
            return pe.get_offset_from_rva(data_entry.struct.OffsetToData), data_entry.struct.Size
    raise KeyError(f"resource {resource_id} not found")


def repack(exe_in: Path, exe_out: Path, bins: dict[int, Path]) -> dict:
    pe = pefile.PE(str(exe_in))
    buffer = bytearray(Path(exe_in).read_bytes())
    replaced = []
    for resource_id, source in bins.items():
        offset, size = find_resource_offset(pe, resource_id)
        data = Path(source).read_bytes()
        if len(data) != size:
            raise ValueError(
                f"resource {resource_id} size mismatch: on-disk {size}, replacement {len(data)} "
                "(size-changing edits are not supported)"
            )
        buffer = patch_bytes(buffer, offset, data)
        replaced.append(resource_id)
    exe_out = Path(exe_out)
    exe_out.write_bytes(bytes(buffer))
    return {
        "in": str(exe_in),
        "out": str(exe_out),
        "replaced": sorted(replaced),
        "in_sha256": hashlib.sha256(Path(exe_in).read_bytes()).hexdigest(),
        "out_sha256": hashlib.sha256(bytes(buffer)).hexdigest(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.repack_updater.repack_win")
    parser.add_argument("exe_in", type=Path)
    parser.add_argument("exe_out", type=Path)
    parser.add_argument("--bin-dir", type=Path, required=True, help="directory with the five payload bins")
    args = parser.parse_args(argv)

    bins = {resource_id: args.bin_dir / name for resource_id, name in BIN_RESOURCE_IDS.items()}
    report = repack(args.exe_in, args.exe_out, bins)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
