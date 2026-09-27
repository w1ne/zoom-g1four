# E1-alt: updater static analysis (2026-09-27)

Goal: answer the "does the updater transfer FS.bin?" question without touching
the device, by scanning the official Mac and Windows updater binaries for ZD2
protocol signatures and payload names. Scanner: `tools/capture/analyze_updater.py`.

**Revision (review fix).** The first version counted raw byte occurrences and
reported hits that came almost entirely from embedded payload resources. The
scanner now subtracts payload blobs (`--exclude`) so counts reflect the updater
code/data region, and the findings below use the corrected code-only counts.
The earlier claims that `60 05`, `60 20 02` and `60 23` counts were above chance
or evidence of a write path are withdrawn — those hits were payload content.

## Method and inputs

- Mac: `Contents/MacOS/EFX Updater`, Mach-O 64-bit x86_64, 320,224 bytes.
- Windows: `ZOOM G1 FOUR System v2.00 Updater.exe`, PE32 x86, 4,193,320 bytes.
- Payloads (sha256-verified from P0): `firmware/extracted/ROM.bin`,
  `Main.bin`, `FS.bin`, `MAIN_INFO.bin`, `Preset.bin` (3,843,940 bytes total).
- Exclusion: for every signature and string,
  `binary_count - sum(payload_count)`. This is exact when a payload is embedded
  verbatim; for the Windows EXE each payload was located as one contiguous blob
  in the image (whole-resource `bytes.find`), so every embedded occurrence is
  removed exactly once. The Mac binary does not embed payload bytes (payloads
  ship as separate files under `Contents/Resources/`), so it is scanned without
  exclusions; `--exclude` is only meaningful for the EXE. Applying the same
  exclusions to the Mac binary drives counts negative, which is itself
  confirmation that its payloads are not embedded.
- Windows code+data outside the five payload resources is ~0.35 MB
  (4,193,320 − 3,843,940 = 349,380 bytes).

Reproduce:

```bash
MAC_APP=$(find .work/p0/mac -name "EFX Updater" | head -1)
WIN_EXE=$(find .work/p0/win -name "*.exe" | head -1)

# Windows: subtract embedded payload bytes
.venv/bin/python -m tools.capture.analyze_updater "$WIN_EXE" \
  --exclude firmware/extracted/ROM.bin --exclude firmware/extracted/Main.bin \
  --exclude firmware/extracted/FS.bin --exclude firmware/extracted/MAIN_INFO.bin \
  --exclude firmware/extracted/Preset.bin

# Mac: no embedded payloads, so no exclusions
.venv/bin/python -m tools.capture.analyze_updater "$MAC_APP"

# Regression test on freshly extracted binaries (downloads packages):
.venv/bin/python -m pytest tools/capture/tests/test_integration.py -m integration -v
```

## Verbatim code-only output

Windows EXE, with payload exclusions:

```
== .work/p0/win/G1 FOUR_v2.00_Win_E/ZOOM G1 FOUR System v2.00 Updater.exe (4193320 bytes)
  enter_update_mode_01         0
  file_ack_60_05               1
  file_api_60_09               1
  file_api_60_27               0
  file_close_60_21             0
  file_delete_60_24            3
  file_list_60_25              2
  file_list_next_60_26         0
  file_open_other_60_20_00     0
  file_open_other_60_20_03     0
  file_open_read_60_20_02      0
  file_open_write_60_20_01     0
  file_read_block_60_22        0
  file_upload_block_60_23      0
  patch_download_opcode_46     0
  patch_upload_opcode_45       0
  pcmode_off_53                0
  pcmode_on_52                 0
  str FLST_SEQ.ZT2             0
  str FS.bin                   0
  str G1 IV                    0
  str G1X IV                   0
  str GUARDZDL.ZT2             0
  str MAIN_INFO.bin            0
  str Main.bin                 0
  str Preset.bin               0
  str ROM.bin                  0
```

Mac binary (already code-only; no exclusions):

```
== .work/p0/mac/G1 FOUR_v2.00_Mac_E/ZOOM G1 FOUR System v2.00 Updater.app/Contents/MacOS/EFX Updater (320224 bytes)
  enter_update_mode_01         0
  file_ack_60_05               0
  file_api_60_09               0
  file_api_60_27               0
  file_close_60_21             0
  file_delete_60_24            2
  file_list_60_25              2
  file_list_next_60_26         0
  file_open_other_60_20_00     0
  file_open_other_60_20_03     0
  file_open_read_60_20_02      0
  file_open_write_60_20_01     0
  file_read_block_60_22        1
  file_upload_block_60_23      0
  patch_download_opcode_46     0
  patch_upload_opcode_45       0
  pcmode_off_53                0
  pcmode_on_52                 0
  str FLST_SEQ.ZT2             0
  str FS.bin                   0
  str G1 IV                    0
  str G1X IV                   0
  str GUARDZDL.ZT2             0
  str MAIN_INFO.bin            0
  str Main.bin                 0
  str Preset.bin               0
  str ROM.bin                  0
```

## Interpretation

### The raw hits were payload content

Subtracting the five payload blobs removes essentially every hit the first
version reported:

| Fragment | Raw count | Code-only |
|---|---|---|
| `60 23` (upload block) | 23 | 0 |
| `60 22` (read block) | 73 | 0 |
| `60 05` (ack) | 296 | 1 |
| `60 20 00` (open other) | 17 | 0 |
| `60 20 02` (open read) | 7 | 0 |
| `60 20 03` (open other) | 4 | 0 |
| `60 09` (close follow-up) | 66 | 1 |
| `GUARDZDL.ZT2` / `FLST_SEQ.ZT2` | 5 / 5 | 0 / 0 |
| `G1 IV` / `G1X IV` | 2 / 1 | 0 / 0 |

The ZT2 strings occurred inside the embedded FS.bin resource and `G1 IV` inside
the embedded Main.bin resource; those resources are referenced by numeric PE
resource ID (129/133/136/139/142), so no payload filename literal exists in the
EXE at all. The raw counts that looked like protocol evidence were the payload
data itself.

### All non-payload counts are at or below chance

In ~0.35 MB of code+data outside the resources, a specific two-byte fragment is
expected ~5.3 times by chance and a specific three-byte fragment ~0.02 times
(the ~0.25 per three-byte figure applies only if the full 4.19 MB image,
including embedded payloads, is treated as uniform data).

- Windows code-only nonzeros: `60 05` (1), `60 09` (1), `60 24` (3),
  `60 25` (2) — four two-byte fragments, all at or below the ~5.3 baseline.
  Every three-byte fragment is 0. Every payload-name string is 0.
- Mac code-only nonzeros: `60 24` (2), `60 25` (2), `60 22` (1) — all at or
  below the ~4.9 two-byte baseline for a 320 KB binary; every three-byte
  fragment is 0.

So the byte signatures in the code regions provide **no positive evidence
either way**: not for a write path, not for a read path, and not for payload
selection. In particular, the write-open fragment `60 20 01` is 0 in both
code regions, and the read-open fragment `60 20 02` is 0 as well.

### Non-signature evidence (unchanged; this is the strong part)

- The Windows EXE embeds all five payloads verbatim as PE resources 129
  (Main.bin), 133 (Preset.bin), 136 (FS.bin), 139 (MAIN_INFO.bin), 142
  (ROM.bin), each located as one contiguous blob at offsets `0x4aa28`,
  `0xc318c`, `0xce18c`, `0x3cc18c`, `0x3cd18c` and byte-identical to
  `firmware/extracted/` (sha256 verified).
- The Mac binary contains the payload table
  `Main\0MAIN_INFO\0FS\0Preset\0ROM\0` followed by five 32-hex-digit MD5s that
  match the five shipped payloads byte-for-byte, including
  `edc06e42361b249ed193cc61eb529453` = MD5(`FS.bin`), plus the runtime format
  string `%@.bin dosen't exist.` — `FS` is explicitly in the payload set.
- The Mac binary exposes an Objective-C FFS write API:
  `allocateFFSOpen:openFlag:`, `allocateFFSWrite:dataBody:`,
  `allocateFFSUnlink:`, `sendSysexFFSWrite:dataBody:receiveBlock:failedBlock:completion:error:`,
  `allocateFFSModeStart:` / `allocateFFSModeEnd:`. Open mode is a runtime
  `openFlag:` argument, so the scanner cannot see it as a byte literal.

## FS.bin conclusion

**Inconclusive (E1 required).**

- For transfer: FS.bin ships in both official packages; the Mac updater lists
  `FS` in its payload table with the matching MD5; an FFS write API exists; the
  five PE resources are byte-identical to the extracted bins.
- Against a firm "IS transferred" claim: no opcode is evidenced in code. All
  code-region opcode counts are at or below chance, the write-open fragment
  `60 20 01` is absent (0/0), and on Mac the open mode is a runtime argument.
  Whether the shipped `FS.bin` is actually streamed on a stock G1 Four, skipped
  by a runtime condition, or only sent for certain models/versions cannot be
  decided from byte signatures; public reports state that official update mode
  does not restore the filesystem on G1 Four.

## E3 / P3 note

The E3 read-path gate likewise has no evidenced read opcode in code:
code-only `file_open_read_60_20_02` is 0 in both binaries and
`file_read_block_60_22` is 0 (EXE) / 1 (Mac, at chance). The P2 plan only
attempts the E3 read-path probe if E1/E1-alt evidence a read opcode; with none,
**chip-off remains the P3 primary path**.

## Caveat

This scanner finds byte signatures, not control flow. Counts in an executable
image cannot prove that code paths execute; the conclusion above is
evidence-weighted, not proof.
