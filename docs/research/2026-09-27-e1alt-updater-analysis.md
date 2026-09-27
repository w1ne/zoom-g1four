# E1-alt: updater static analysis (2026-09-27)

Goal: answer the "does the updater transfer FS.bin?" question without touching
the device, by scanning the official Mac and Windows updater binaries for ZD2
protocol signatures and payload names. Scanner: `tools/capture/analyze_updater.py`.
Confidence tags follow `2026-09-27-prior-art.md`.

## Command and inputs

```bash
MAC_APP=$(find .work/p0/mac -name "EFX Updater" | head -1)
WIN_EXE=$(find .work/p0/win -name "*.exe" | head -1)
.venv/bin/python -m tools.capture.analyze_updater "$MAC_APP" "$WIN_EXE" --json > .work/p2/e1alt-report.json
.venv/bin/python -m tools.capture.analyze_updater "$MAC_APP" "$WIN_EXE"
```

- Mac: `Contents/MacOS/EFX Updater`, Mach-O 64-bit x86_64, 320,224 bytes.
- Windows: `ZOOM G1 FOUR System v2.00 Updater.exe`, PE32 x86, 4,193,320 bytes.

## Verbatim scan output

```
== .work/p0/mac/G1 FOUR_v2.00_Mac_E/ZOOM G1 FOUR System v2.00 Updater.app/Contents/MacOS/EFX Updater (320224 bytes)
  enter_update_mode_01         0
  file_ack_60_05               0
  file_close_60_21             0
  file_delete_60_24            2
  file_list_60_25              2
  file_list_next_60_26         0
  file_open_read_60_20_02      0
  file_open_write_60_20_01     0
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
== .work/p0/win/G1 FOUR_v2.00_Win_E/ZOOM G1 FOUR System v2.00 Updater.exe (4193320 bytes)
  enter_update_mode_01         0
  file_ack_60_05               296
  file_close_60_21             50
  file_delete_60_24            20
  file_list_60_25              7
  file_list_next_60_26         25
  file_open_read_60_20_02      7
  file_open_write_60_20_01     0
  file_upload_block_60_23      23
  patch_download_opcode_46     0
  patch_upload_opcode_45       0
  pcmode_off_53                0
  pcmode_on_52                 0
  str FLST_SEQ.ZT2             5
  str FS.bin                   0
  str G1 IV                    2
  str G1X IV                   1
  str GUARDZDL.ZT2             5
  str MAIN_INFO.bin            0
  str Main.bin                 0
  str Preset.bin               0
  str ROM.bin                  0
```

## Interpretation

**Full packets are not stored as literals.** All four-byte `52 00 6e xx`
signatures are zero in both binaries, and the bare `52 00 6e` address prefix
occurs once in the 4.19 MB EXE and zero times in the Mac binary. The binaries
assemble SysEx packets at runtime; only fragments appear in the image.
Consequently absence of a fragment is weak evidence of absence of the code
path that would emit it.

**Short-fragment counts must be read against chance.** In uniform random data a
specific two-byte sequence is expected ~64 times in the 4.19 MB EXE and ~5
times in the 320 KB Mac binary; a specific three-byte sequence ~0.25 and ~0.02
times. Much of the EXE is embedded payload data, which further skews baselines.
Of the two-byte signatures, only `file_ack_60_05` (296) stands clearly above
chance; `file_upload_block_60_23` (23), `file_delete_60_24` (20),
`file_close_60_21` (50), `file_list_60_25` (2) and `file_list_next_60_26` (25)
are near or below the expected chance rate and cannot establish calls on their
own. `file_open_read_60_20_02` (7) is a three-byte fragment and is far above
the ~0.25 chance rate.

**Payload-name strings are absent by design.** No payload filename string is
present in the EXE, not even `.bin`. Payloads are referenced by numeric PE
resource IDs, not names, so name-string absence carries no signal on Windows.
The ZT2 strings that were found are payload *content*, not code references:
`GUARDZDL.ZT2`/`FLST_SEQ.ZT2` each occur 4 times inside the embedded FS.bin
resource (resource 136) and 5 times in the EXE overall; `G1 IV` occurs inside
the embedded Main.bin resource (129).

**File-open modes (Windows EXE).** Read-open `60 20 02` present (7). Write-open
`60 20 01` absent (0). Neighbouring mode fragments `60 20 00` (17) and
`60 20 03` (4) are present well above chance; their meaning is unknown, but the
open-mode byte is evidently not a single hard-coded literal.

**Block transfer (Windows EXE).** Block-write fragment `60 23` present (23,
near chance); read-ack `60 05` (296) and close `60 21` (50) present; delete
`60 24` (20) and list/list-next `60 25`/`60 26` present at counts near chance.

**Mac binary is a different code shape.** Aside from `60 24` (2) and `60 25`
(2), every signature and string is zero, yet the same payloads ship as named
files in `Contents/Resources/`. The binary is Objective-C and exposes an FFS
file API with runtime arguments: `allocateFFSOpen:openFlag:`,
`allocateFFSWrite:dataBody:`, `allocateFFSUnlink:`, `allocateFFSFormat`,
`allocateFFSFileListFlush`, `allocateFFSModeStart:`, `allocateFFSModeEnd:`,
`allocateFFSAck:`, and matching `sendSysexFFS...` selectors. It composes
payload filenames at runtime from the base names `Main`, `MAIN_INFO`, `FS`,
`Preset`, `ROM` and the format string `%@.bin`. Literal scanning therefore
under-reports the Mac updater structurally; its zeros are not evidence that
operations are absent.

## FS.bin conclusion

**Inconclusive (E1 required).**

Evidence that the write path and FS.bin payload exist — all outside the
signature counts:

- Both official packages ship `FS.bin` (3,137,536 B) [V]: as a named resource
  (`Contents/Resources/FS.bin`) on Mac, and embedded verbatim in the EXE as PE
  resource 136 (sha256 `7dd2821c...`, matching the P0 mapping) [V].
- The Mac binary contains the payload table
  `Main\0MAIN_INFO\0FS\0Preset\0ROM\0` followed by five 32-hex-digit MD5s that
  match the five shipped payloads byte-for-byte, including
  `edc06e42361b249ed193cc61eb529453` = MD5(`FS.bin`) [V]. `FS` is explicitly in
  the updater's payload set, and `allocateFFSWrite:dataBody:` /
  `sendSysexFFSWrite:` show a write API exists [V].
- The Windows EXE contains the block-write fragment `60 23` (23) and the
  reference protocol's write path is open-write (`60 20 01`) + block-write
  (`60 23`) [S from prior art].

Evidence against a firm "IS transferred" claim:

- The write-open fragment `60 20 01` is absent from both binaries (0/0), and
  the Mac FFS open takes its mode as a runtime `openFlag:` argument, so the
  scanner cannot observe the write-open path at all.
- The `FS.bin` string is absent from both binaries (0/0); on Mac the name is
  assembled from `FS` + `%@.bin`, and on Windows payloads are numeric resources
  with no name strings, so the string counts cannot confirm which payloads are
  sent.
- Public reports state that official update mode does not restore the
  filesystem on G1 Four (`2026-09-27-prior-art.md`) [V]; whether the shipped
  `FS.bin` is actually streamed, skipped by a runtime condition, or sent under
  another model/version path cannot be decided from byte signatures.

The static evidence shows FS.bin is present in the updater payload set and a
write API exists, which leans toward transfer, but the scanner confirms neither
the open-write step nor the selection of FS.bin for sending. E1 (live
bidirectional capture of a real update session) is required to settle it.

## Caveat

This scanner finds byte signatures, not control flow. Counts in an executable
image cannot prove that code paths execute; the conclusion above is
evidence-weighted, not proof.
