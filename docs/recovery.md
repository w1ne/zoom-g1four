# Recovery playbook (living document)

Status: initial notes only — expand before any write operation is performed.

## When to use

Any state where the pedal does not boot normally or the effects/filesystem is
unexpectedly corrupt.

## Escalation order

1. **Official re-flash retry.** Enter update mode (hold both footswitches while
   plugging USB), run the pristine official updater. Retryable; does not
   restore the filesystem on G1 Four.
2. **Filesystem rebuild via SPI EEPROM pin short.** Community-reported fix for
   a corrupt FS where the pedal hangs at boot: short the SPI EEPROM data pin to
   GND through ~100 Ohm during boot to force a rebuild. Sources:
   mungewell/zoom-zt2 issues #53, #100; reddit r/zoommultistomp
   "Zoom G1Four stuck up while booting". Requires opening the unit.
3. **Chip-off reflash (last resort).** Desolder / clip the MX25L3233F, write a
   known-good 4 MB image with CH341A/RT809H/flashrom, verify, reassemble.
   Requires the P2 dump or a donor dump from an identical model.

## Rules

- `firmware/official/` downloads are never edited.
- No FS write until backups exist and verify (CRC) against the current state.
- No `Main.bin` flashing until the P2 full-chip dump exists and has a tested
  restore path.
- Record every operation (tool, command, hashes, observed result) in `backups/`
  manifests — recovery depends on knowing exactly what changed.
