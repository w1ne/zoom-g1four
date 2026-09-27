"""E5: replace PE resource payloads inside the Windows updater EXE.

Same-size payloads are patched in place at the resource data offsets reported
by pefile, preserving every other byte of the EXE. Payload size changes are
rejected (recorded as a limitation; the Mac .app path or a full PE resource
rewriter would be needed for size-changing edits).

Note for P5a: byte patching invalidates the Authenticode signature and leaves
the PE checksum stale; Windows user-mode EXEs ignore the checksum, but expect
SmartScreen/UAC "Unknown publisher" friction.
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
    if offset < 0 or offset + len(data) > len(buffer):
        raise ValueError(
            f"patch out of range: offset {offset}, length {len(data)}, buffer {len(buffer)}"
        )
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
    exe_in = Path(exe_in)
    exe_out = Path(exe_out)
    if not exe_in.is_file():
        raise FileNotFoundError(f"no such EXE: {exe_in}")
    data = exe_in.read_bytes()
    in_sha256 = hashlib.sha256(data).hexdigest()
    pe = pefile.PE(data=data)
    try:
        buffer = bytearray(data)
        replaced = []
        for resource_id, source in bins.items():
            offset, size = find_resource_offset(pe, resource_id)
            replacement = Path(source).read_bytes()
            if len(replacement) != size:
                raise ValueError(
                    f"resource {resource_id} size mismatch: on-disk {size}, replacement {len(replacement)} "
                    "(size-changing edits are not supported)"
                )
            if offset + size > len(buffer):
                raise ValueError(f"resource {resource_id} range out of file bounds")
            buffer = patch_bytes(buffer, offset, replacement)
            replaced.append(resource_id)
    finally:
        pe.close()
    exe_out.write_bytes(bytes(buffer))
    return {
        "in": str(exe_in),
        "out": str(exe_out),
        "replaced": sorted(replaced),
        "in_sha256": in_sha256,
        "out_sha256": hashlib.sha256(bytes(buffer)).hexdigest(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.repack_updater.repack_win")
    parser.add_argument("exe_in", type=Path)
    parser.add_argument("exe_out", type=Path)
    parser.add_argument("--bin-dir", type=Path, required=True, help="directory with the five payload bins")
    args = parser.parse_args(argv)

    bins = {resource_id: args.bin_dir / name for resource_id, name in BIN_RESOURCE_IDS.items()}
    try:
        report = repack(args.exe_in, args.exe_out, bins)
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"error: {error} (bin dir: {args.bin_dir})")
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
