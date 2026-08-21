# Client versions supported by ArcheaAge (multi-version launcher)

Researched 2026-08-19. Source of truth: the official
[AAEmu-Launcher](https://github.com/ZeromusXYZ/AAEmu-Launcher) `AAEmu.Common.Launcher/*.cs`
and the [AAEmu wiki](https://github.com/AAEmu/AAEmu/tree/develop/docs/wiki).

The AAEmu server protocol family covers **7 client versions**. Each client has a
different login protocol, executable path and launch arguments.

## Version table

| # | `loginType` (manifest) | Client | Version | exe (relative to install) | Launch arguments |
|---|---|---|---|---|---|
| 1 | `trino_1_2` | Trion (EN) | 1.2 | `bin32/archeage.exe` | `-t +auth_ip <ip> -auth_port <port> -handle 00000000:00000000 -lang en_us` |
| 2 | `trino_3_5` | Trion (EN) | 3.5 | `bin32/archeage.exe` | `-t +auth_ip <ip> -auth_port <port> -handle 00000000:00000000 -lang en_us` |
| 3 | `trino_6_0` | Trion (EN) | 6.0 | `bin64/archeage.exe` | `-t +auth <ip> -auth_port <port> -handle 00000000:00000000 -lang en_us -time_offset 300` |
| 4 | `trino_7_0` | Trion (EN) | 7.0 | `launch_game.exe` | `-eac_launcher_settings settings_32.json -t +auth_ip <ip> -auth_port <port> -handle 00000000:00000000 -lang en_us` |
| 5 | `kakao_8_0` | Kakao (KR) | 8.0 | `bin64/archeage.exe` | `-t +auth_ip <ip> -auth_port <port> -authtoken <token>` |
| 6 | `mailru_1_0` | Mail.ru (RU) | 0.5 / 1.0 | `bin32/archeage.exe` | `-r +auth_ip <ip>:<port> -uid <user> -token <pass>` |
| 7 | `xlworld_1_0` | XLGames World (global) | 1.0 | `bin64/archeage.exe` | `<token> -k` |

> Gamigo (EU), Taiwan and Tencent are regional builds **not** in the official
> launcher list — they need a custom login protocol shim. The 7 above are the
> ones AAEmu's launcher + login server are designed for.

## Downloads (official AAEmu sources)

The AAEmu wiki (docs/wiki/Client.md + Dependencies-and-Downloads.md) publishes:

| Version | Source |
|---|---|
| 1.2 | MEGA folder `GnwjQCrZ#WNWzX_lDvkzCqoTtt7I42Q` · MEGA `Trion_1.2_(r208022)_BROC_FULL_PATCHED_CLIENT.zip` (folder `C3Q0WQjT` file `qyAVQY4I`) · Google Drive `1_pIBVHIm1YFal-nteGaVuXjTv3Yrsv4Q` |
| 3.5 / 6.0 / 7.0 / Kakao 8.0 / Mail.ru 1.0 / XLGames World 1.0 | MEGA "client directory (multiple versions)" `C3Q0WQjT#vRUethZLPiYSo2B4nE_etg` · AAEmu Discord `#client-downloads` |

## Distribution pipeline (S3 / HTTP CDN)

The launcher already supports `https://` URLs in manifests (`content/manifests/{v}.json`),
so any HTTP server or S3 bucket works:

1. Download a client + extract it (see `scripts/upload-client.sh`).
2. Upload the folder to S3: `aws s3 sync <client> s3://<bucket>/archeaage/{version}/`.
3. Generate the manifest: `scripts/upload-client.sh <version> <client-dir>` writes
   `content/manifests/{version}.json` with S3 URLs + SHA256 + verify entries.
4. Register the version in `apps/registry/appsettings.json` (`Versions` + `Tokens`).
5. The launcher shows it as a version chip and launches with the table above.

Per-version verify entries (game_pak/bin32/exe) and the client structure differ —
set them per version in the manifest (`verify` array).
