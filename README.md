# yt-dlp-sbs

An unofficial Linux downloader for SBS On Demand, using [yt-dlp](https://github.com/yt-dlp/yt-dlp) and the [SBS extractor plugin](https://github.com/phil2803/yt-dlp-sbsfix).

Downloads available episodes from an SBS show or season URL, with `S01/S02` season directories and `S01E01` filenames. Includes dependency checks and a preview mode.

## Quick start

```bash
python3 yt-dlp-sbs.py --setup-only
python3 yt-dlp-sbs.py "https://www.sbs.com.au/ondemand/tv-series/8-out-of-10-cats-does-countdown"
python3 yt-dlp-sbs.py "https://www.sbs.com.au/ondemand/tv-series/8-out-of-10-cats-does-countdown/season-9" --download
```

For custom output locations use `--output-dir /path/to/tv`. By default, existing episodes are skipped. Add `--replace` to replace matching episodes after the new video has passed a basic FFprobe check.

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
