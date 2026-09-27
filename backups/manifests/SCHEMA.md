# Backup manifest schema (version 1)

One JSON file per backup, named `<state_digest>.json`, written to
`backups/manifests/`. Artifacts live under `backups/<state_digest>/`.

| Field | Meaning |
|---|---|
| `schema_version` | 1 |
| `created_utc` | ISO-8601 UTC timestamp |
| `identity` | pedal identity: `reply_hex`, `model_bytes`, `model`, `firmware` |
| `patch_bank` | `count`, `patch_size`, `bank_size` from the pedal |
| `patches[]` | per location: `location`, `sha256`, `size`, `read_seconds`, `crc32_device_ok` |
| `fs.files[]` | per file: `name`, `sha256`, `size`, `read_seconds`, `crc32_device_ok` |
| `fs.listing_seconds` | seconds spent enumerating the file listing |
| `oracle` | `source` path plus `device_only` / `oracle_only` name lists (informational) |
| `timings` | `patch_total_seconds`, `fs_total_seconds`, `total_seconds` |
| `state_digest` | sha256 over `schema_version` + identity + patch bank + per-patch (`location`, `sha256`) + per-file (`name`, `sha256`), canonical JSON |

`crc32_device_ok` is `true` in a successful run: any device CRC mismatch aborts
the backup with a `PedalError`. Empty payloads (length 0) carry no device CRC
and are recorded `true` without a CRC check.
