#!/usr/bin/env python3
"""SBS On Demand series/season downloader for Linux (version 3.0).

Automatically checks yt-dlp, FFmpeg, curl, and the SBS extractor plugin.
System package installation requires confirmation unless --yes is given.
Default action is preview; add --download to save episodes.
"""
import argparse
import ast
import getpass
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

PLUGIN_URL = ("https://raw.githubusercontent.com/phil2803/yt-dlp-sbsfix/main/"
              "yt-dlp-plugins/sbsfix/yt_dlp_plugins/extractor/sbsfix.py")
PLUGIN_RELATIVE = Path(".config/yt-dlp/plugins/sbsfix/yt_dlp_plugins/extractor/sbsfix.py")
SHOW_PATH = re.compile(r'^/ondemand/tv-series/([a-z0-9-]+)(?:/season-(\d+))?/?$')
EPISODE_PATH = re.compile(
    r'/ondemand/tv-series/(?P<show>[a-z0-9-]+)/season-(?P<season>\d+)/'
    r'(?P<slug>[a-z0-9-]+)/(?P<id>\d{10,})')
SEASON_PATH = re.compile(r'/ondemand/tv-series/(?P<show>[a-z0-9-]+)/season-(?P<season>\d+)(?:[/"?\\]|$)')
NUMBER_IN_SLUG = re.compile(r'(?:^|-)s(\d+)-ep(\d+)(?:-|$)', re.I)
NUMBER_IN_FILE = re.compile(r'(?i)(?<![a-z0-9])s(\d{1,3})[ ._-]*e(\d{1,3})(?!\d)')
VIDEO_EXTS = {'.mp4', '.mkv', '.m4v', '.webm', '.avi', '.ts'}


def execute(command, *, capture=False):
    return subprocess.run(command, text=True, check=False,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None)


def plugin_active():
    if not shutil.which('yt-dlp'):
        return False
    proc = execute(['yt-dlp', '-v', '--list-extractors'], capture=True)
    output = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode == 0 and 'Extractor Plugins: sbsfix (SBSIE)' in output


def package_command(missing):
    packages = sorted({'ffmpeg' if x in ('ffprobe', 'ffmpeg') else x for x in missing})
    if shutil.which('pacman'):
        return ['sudo', 'pacman', '-S', '--needed', *packages]
    if shutil.which('dnf'):
        return ['sudo', 'dnf', 'install', *packages]
    if shutil.which('apt-get'):
        return ['sudo', 'apt-get', 'install', *packages]
    return None


def permission(question, yes):
    if yes:
        return True
    if not sys.stdin.isatty():
        return False
    return input(f'{question} [y/N]: ').strip().lower() in ('y', 'yes')


def install_plugin():
    target = Path.home() / PLUGIN_RELATIVE
    print(f'Downloading SBS plugin from {PLUGIN_URL}', flush=True)
    request = urllib.request.Request(PLUGIN_URL, headers={'User-Agent': 'yt-dlp-sbs/3.0'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read(256 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f'Cannot download SBS plugin: {exc}') from exc
    if len(content) > 256 * 1024 or not content:
        raise RuntimeError('SBS plugin download is missing or unexpectedly large')
    try:
        ast.parse(content.decode('utf-8'), filename='sbsfix.py')
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise RuntimeError(f'Downloaded plugin is not valid Python: {exc}') from exc
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.sbsfix-', suffix='.py', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fchmod(stream.fileno(), 0o644)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    print(f'Installed SBS plugin: {target}')


def setup_dependencies(yes=False, no_install=False):
    required = ['yt-dlp', 'ffmpeg', 'ffprobe', 'curl']
    missing = [program for program in required if not shutil.which(program)]
    if missing:
        print(f'Missing system commands: {", ".join(missing)}')
        command = package_command(missing)
        if not command:
            raise RuntimeError('Cannot identify supported package manager; install missing commands manually')
        print('Suggested installation: ' + ' '.join(command))
        if no_install or not permission('Install missing system packages?', yes):
            raise RuntimeError('Required system packages are missing; no changes made')
        proc = execute(command)
        if proc.returncode:
            raise RuntimeError(f'Package installation failed (exit {proc.returncode})')
        still_missing = [program for program in required if not shutil.which(program)]
        if still_missing:
            raise RuntimeError('Commands still missing after installation: ' + ', '.join(still_missing))
    else:
        print('System dependencies: OK (yt-dlp, FFmpeg, curl)')
    if plugin_active():
        print('SBS extractor plugin: OK (sbsfix)')
        return
    print('SBS extractor plugin: not detected')
    if no_install or not permission('Install SBS extractor plugin from phil2803/yt-dlp-sbsfix?', yes):
        raise RuntimeError('SBS plugin not installed; no changes made')
    install_plugin()
    if not plugin_active():
        raise RuntimeError('Installed plugin but yt-dlp did not load it. Check yt-dlp -v output.')
    print('SBS extractor plugin: OK (sbsfix)')


def get_page(url):
    result = execute(['curl', '-fLsS', '--retry', '2', '--connect-timeout', '15',
                      '--max-time', '40', '--compressed', url], capture=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f'curl exited {result.returncode}')
    return html.unescape(result.stdout).replace('\\/', '/')


def season_numbers(document, show):
    return {int(match.group('season')) for match in SEASON_PATH.finditer(document)
            if match.group('show') == show}


def parse_episodes(document, show, selected_season):
    matches = {}
    for m in EPISODE_PATH.finditer(document):
        if m.group('show') != show:
            continue
        season = int(m.group('season'))
        if selected_season is not None and season != selected_season:
            continue
        slug_info = NUMBER_IN_SLUG.search(m.group('slug'))
        if not slug_info or int(slug_info.group(1)) != season:
            continue
        episode = int(slug_info.group(2))
        matches.setdefault((season, episode), set()).add(m.group('id'))
    return matches


def discover(show, selected_season, start_page):
    pages = {selected_season: start_page} if selected_season is not None else {}
    if selected_season is None:
        numbers = season_numbers(start_page, show)
        numbers |= {season for season, _ in parse_episodes(start_page, show, None)}
        if not numbers:
            raise RuntimeError('No season links found on the show page. No changes made.')
        pages = {season: None for season in sorted(numbers)}
    collected = {}
    failed = []
    for season in sorted(pages):
        url = f'https://www.sbs.com.au/ondemand/tv-series/{show}/season-{season}'
        print(f'Scanning season {season}: {url}', flush=True)
        try:
            document = pages[season] if pages[season] is not None else get_page(url)
        except RuntimeError as exc:
            failed.append(season)
            print(f'WARNING: Cannot read season {season}: {exc}', file=sys.stderr)
            continue
        for key, ids in parse_episodes(document, show, season).items():
            collected.setdefault(key, set()).update(ids)
    return collected, failed


def show_name_from_slug(slug):
    small = {'a', 'an', 'and', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to'}
    words = slug.split('-')
    return ' '.join(w.upper() if w.isdigit() else
                    (w if i and w in small else w.capitalize())
                    for i, w in enumerate(words))


def existing_episodes(root, season, episode):
    folder = root / f'S{season:02d}'
    if not folder.is_dir():
        return []
    matches = []
    for entry in folder.iterdir():
        if entry.is_file() and entry.suffix.lower() in VIDEO_EXTS:
            found = NUMBER_IN_FILE.search(entry.stem)
            if found and (int(found.group(1)), int(found.group(2))) == (season, episode):
                matches.append(entry)
    return sorted(matches)


def valid_download(path):
    if not path.is_file() or path.stat().st_size < 1_000_000:
        raise RuntimeError('Video missing or too small')
    result = execute(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                      '-of', 'default=noprint_wrappers=1:nokey=1', str(path)], capture=True)
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        duration = 0
    if result.returncode or duration < 300:
        raise RuntimeError('Video failed FFprobe duration check')


def make_netrc(folder, username, password):
    def quote(value):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if '\n' in username + password or '\r' in username + password:
        raise RuntimeError('Credentials must not contain newlines')
    path = folder / 'account.netrc'
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w') as out:
        out.write(f'machine sbs login {quote(username)} password {quote(password)}\n')
    return path


def download_one(root, title, season, episode, video_id, netrc, replace):
    code = f'S{season:02d}E{episode:02d}'
    dest_dir = root / f'S{season:02d}'
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'.sbs-{code}-', dir=root) as temporary:
        stage = Path(temporary)
        name = f'{title} - {code}'
        url = f'https://www.sbs.com.au/ondemand/watch/{video_id}'
        args = ['yt-dlp', '--no-playlist', '--netrc', '--netrc-location', str(netrc),
                '-f', 'bv*+ba/b', '--merge-output-format', 'mp4', '--no-overwrites',
                '--no-write-info-json', '--no-write-thumbnail',
                '-o', str(stage / (name + '.%(ext)s')), url]
        run = execute(args)
        if run.returncode:
            raise RuntimeError(f'yt-dlp failed (exit {run.returncode})')
        output = [p for p in stage.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
        if len(output) != 1:
            raise RuntimeError(f'Expected one video; found {len(output)}')
        incoming = output[0]
        valid_download(incoming)
        old = existing_episodes(root, season, episode)
        if old and not replace:
            print(f'SKIP {code}: a video appeared during download')
            return False
        destination = dest_dir / incoming.name
        if destination.exists() and destination not in old:
            raise RuntimeError(f'Target already exists: {destination}')
        backup = stage / 'previous'
        backup.mkdir()
        moved = []
        placed = False
        try:
            for old_path in old:
                back_path = backup / old_path.name
                os.replace(old_path, back_path)
                moved.append((old_path, back_path))
            os.replace(incoming, destination)
            placed = True
        except Exception:
            if placed and destination.exists():
                destination.unlink()
            for original, back_path in reversed(moved):
                if back_path.exists():
                    os.replace(back_path, original)
            raise
        print(f'SAVED {code}: {destination} (replaced {len(old)} old video(s))', flush=True)
        return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', nargs='?', help='SBS show or season page URL')
    parser.add_argument('--setup-only', action='store_true', help='Check/install dependencies then exit')
    parser.add_argument('--yes', action='store_true', help='Approve installing missing dependencies and SBS plugin')
    parser.add_argument('--no-install', action='store_true', help='Do not install packages or plugin')
    parser.add_argument('--output-dir', type=Path, default=Path('.'),
                        help='Parent output folder (default: current directory)')
    parser.add_argument('--download', action='store_true', help='Download episodes (default: preview)')
    parser.add_argument('--replace', action='store_true',
                        help='Replace existing episode videos after a successful download')
    parser.add_argument('--email', help='SBS login email; otherwise prompt on download')
    args = parser.parse_args()
    if not args.url and not args.setup_only:
        parser.error('Supply an SBS show/season URL or use --setup-only')
    try:
        setup_dependencies(yes=args.yes, no_install=args.no_install)
    except (RuntimeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    if args.setup_only:
        return 0
    parsed = urlparse(args.url)
    match = SHOW_PATH.fullmatch(parsed.path)
    if parsed.scheme != 'https' or parsed.hostname not in {'www.sbs.com.au', 'sbs.com.au'} or not match:
        parser.error('Expected https://www.sbs.com.au/ondemand/tv-series/SHOW[/season-N]')
    slug = match.group(1)
    requested_season = int(match.group(2)) if match.group(2) is not None else None
    if requested_season == 0:
        parser.error('Season must be greater than zero')
    show_title = show_name_from_slug(slug)
    root = args.output_dir.expanduser().resolve() / show_title
    try:
        document = get_page(args.url)
        episodes, failed_seasons = discover(slug, requested_season, document)
    except RuntimeError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    conflicts = {key: ids for key, ids in episodes.items() if len(ids) != 1}
    valid = {key: next(iter(ids)) for key, ids in episodes.items() if len(ids) == 1}
    for (season, episode), ids in sorted(conflicts.items()):
        print(f'CONFLICT S{season:02d}E{episode:02d}: multiple SBS IDs ({", ".join(sorted(ids))}); skipping')
    todo = []
    for (season, episode), ident in sorted(valid.items()):
        old = existing_episodes(root, season, episode)
        code = f'S{season:02d}E{episode:02d}'
        if old and not args.replace:
            print(f'SKIP {code}: already exists ({len(old)} video file(s))')
        else:
            print(f'{"REPLACE" if old else "ADD"} {code}: SBS video {ident}'
                  + (f' ({len(old)} existing)' if old else ''))
            todo.append((season, episode, ident))
    print(f'Found {len(valid)} unique episodes; {len(conflicts)} conflicts; '
          f'{len(todo)} to {"download" if args.download else "process"}.')
    print(f'Output: {root}')
    if not args.download:
        print('PREVIEW ONLY. Add --download to save files. Add --replace to replace existing videos.')
        return 1 if failed_seasons else 0
    if not todo:
        return 1 if failed_seasons else 0
    email = args.email or input('SBS account email: ').strip()
    if not email:
        print('ERROR: No SBS account email', file=sys.stderr)
        return 1
    password = getpass.getpass('SBS password: ')
    if not password:
        print('ERROR: No SBS password', file=sys.stderr)
        return 1
    root.mkdir(parents=True, exist_ok=True)
    errors = 0
    with tempfile.TemporaryDirectory(prefix='.sbs-auth-', dir=root) as work:
        secret_path = make_netrc(Path(work), email, password)
        del password
        for season, episode, ident in todo:
            code = f'S{season:02d}E{episode:02d}'
            try:
                download_one(root, show_title, season, episode, ident, secret_path, args.replace)
            except (RuntimeError, OSError) as exc:
                errors += 1
                print(f'FAILED {code}: {exc}', file=sys.stderr, flush=True)
    if failed_seasons:
        print(f'WARNING: Could not read seasons: {failed_seasons}', file=sys.stderr)
    print(f'Finished with {errors} download failure(s), {len(conflicts)} conflict(s).')
    return 1 if errors or failed_seasons else 0


if __name__ == '__main__':
    sys.exit(main())
