# yt-dlp-sbs

An unofficial Linux downloader for SBS On Demand, using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and the [SBS extractor plugin](https://github.com/phil2803/yt-dlp-sbsfix).

Downloads available episodes from an SBS show or season URL, with `S01/S02` season directories and `S01E01` filenames. Includes dependency checks, a preview mode, and optional saved SBS credentials.

## Quick start

```bash
python3 yt-dlp-sbs.py --setup-only
python3 yt-dlp-sbs.py "https://www.sbs.com.au/ondemand/tv-series/8-out-of-10-cats-does-countdown"
python3 yt-dlp-sbs.py "https://www.sbs.com.au/ondemand/tv-series/8-out-of-10-cats-does-countdown/season-9" --download
```

For custom output locations use `--output-dir /path/to/tv`. By default, existing episodes are skipped. Add `--replace` to replace matching episodes after the new video has passed a basic FFprobe check.

## Saved SBS credentials (v3.1)

The first download prompts for your SBS email and password. You can choose whether to save them for later runs. Saving is optional and defaults to **No**. If you save them, subsequent downloads reuse the account without a prompt.

Credentials are saved in `~/.config/yt-dlp-sbs/credentials` in yt-dlp-compatible netrc format, with mode `0600` in a `0700` directory. The file contains the password **in plaintext**. It is intended for a trusted user account, including a headless Linux server. Do not add it to Git or share it.

- `--forget-credentials` removes the saved credentials without starting a download.
- `--no-saved-credentials` bypasses stored credentials, prompts for this run, and does not save them.
- `--email ADDRESS` sets the login name only when prompting for fresh credentials; the password is always requested through a hidden terminal prompt.

```bash
python3 yt-dlp-sbs.py --forget-credentials
python3 yt-dlp-sbs.py "SEASON_URL" --download --no-saved-credentials
```

The script now verifies plugin loading using simulated extraction rather than `--list-extractors`, which did not report the plugin reliably on some yt-dlp versions. A simulated extraction may report an authentication error when no account is supplied; that does not mean the plugin failed to load.

## Requirements

Linux, Python 3, curl, yt-dlp, FFmpeg, an SBS account and the SBS extractor plugin. The script can offer installation through pacman, DNF or APT; installation requires user approval unless `--yes` is set. Use `--no-install` to prevent automatic installation.

## Commands

```bash
python3 yt-dlp-sbs.py --help
python3 yt-dlp-sbs.py --setup-only
python3 yt-dlp-sbs.py "SHOW_URL" --download --output-dir /path/to/tv
python3 yt-dlp-sbs.py "SEASON_URL" --download --replace
```

## Limitations

- Available episodes and their season numbers are determined from SBS pages. SBS numbering may not match third-party episode databases.
- Dynamic pages or changes to the SBS website may prevent discovery.
- Conflicting episode IDs are skipped.
- Downloading is not possible for DRM-protected streams through yt-dlp.
- The project is unofficial and not affiliated with SBS. Follow the service's terms and applicable law.

## Credits and licence

Uses yt-dlp and the SBS plugin maintained by [phil2803](https://github.com/phil2803/yt-dlp-sbsfix). Licensed under the GPL-3.0 license in this repository.
