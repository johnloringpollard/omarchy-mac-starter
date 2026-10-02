#!/usr/bin/env python3
"""Install the Mac desktop and optional plugins, then configure plugins yourself."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import plugins
import starter

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd=None, capture=False):
    print('+ ' + shlex.join(map(str, command)), flush=True)
    result = subprocess.run(command, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return (result.stdout or '').strip()


def choose(names):
    if shutil.which('gum'):
        result = subprocess.run(['gum', 'choose', '--no-limit', '--header',
                                 'Optional plugins (Space selects; Enter continues)', *names],
                                check=True, text=True, stdout=subprocess.PIPE)
        return result.stdout.splitlines()
    print('Optional plugins. Leave blank for the desktop and shortcuts only.')
    for index, name in enumerate(names, 1):
        print(f'  {index}. {name}')
    answer = input('Plugin numbers, separated by spaces: ').split()
    if any(not value.isdigit() or not 1 <= int(value) <= len(names) for value in answer):
        raise plugins.Refused('Choose numbers from the list')
    return list(dict.fromkeys(names[int(value) - 1] for value in answer))


def installed(tool, name):
    target, receipt = tool.paths(name)
    plugins.safe_path(tool.home, target)
    plugins.safe_path(tool.home, receipt)
    if not target.exists():
        return False
    if not receipt.exists():
        print(f'{name}: already installed outside this starter; skipped, including backend setup.')
        return True
    saved = json.loads(receipt.read_text())
    module = tool.module(name)
    if (saved.get('module'), saved.get('commit')) != (name, module['commit']):
        raise plugins.Refused(f'{name}: installed receipt differs from locked selection')
    if run(['git', '-C', str(target), 'rev-parse', 'HEAD'], capture=True) != module['commit']:
        raise plugins.Refused(f'{name}: installed Git revision differs from lock')
    print(f'{name}: pinned source already installed; preserving local settings and build output.')
    return True


def backend(tool, name, state, state_path):
    module = tool.module(name)
    if name not in ('magic-mouse', 'airpods', 'airplay'):
        return
    if state['backends'].get(name) == module['commit']:
        return
    target, receipt = tool.paths(name)
    if name == 'airplay':
        if not sys.stdin.isatty():
            raise plugins.Refused('AirPlay service setup needs an interactive terminal; rerun setup there')
        if not shutil.which('doubletake'):
            run(['omarchy', 'pkg', 'aur', 'add', 'doubletake-git'])
        run(['sudo', 'systemctl', 'enable', '--now', 'avahi-daemon'])
    else:
        script = module['setup'][1]
        saved = json.loads(receipt.read_text())
        entry = target / script
        plugins.safe_path(tool.home, entry)
        if saved['files'].get(script) != ['file', plugins.digest(entry.read_bytes()), entry.stat().st_mode & 0o777]:
            raise plugins.Refused(f'{name}: backend installer changed; refusing to execute it')
        run(module['setup'], cwd=target)
    state['backends'][name] = module['commit']
    plugins.atomic_json(state_path, state)


def setup(home, selected, sandbox=False):
    tool = plugins.Plugins(home, sandbox=sandbox)
    home_args = ['--home', str(home)] if sandbox else []
    core = [str(ROOT / 'install'), *home_args]
    journal_path = home / '.local/state/omarchy-mac-starter/journal.json'
    plugins.safe_path(home, journal_path)
    journal = json.loads(journal_path.read_text()) if journal_path.exists() else None
    if journal and (journal.get('version') != 1 or journal.get('home') != str(home)):
        raise plugins.Refused('Core journal version or home does not match')
    configured = bool(journal and journal.get('status') == 'installed')
    if (configured and 'desktop' in journal.get('modules', [])
            and not (home / starter.APPEARANCE).is_file()):
        raise plugins.Refused('This desktop predates appearance controls. Switch to another theme, uninstall it, then rerun setup; see docs/migration.md')
    # New installs must reject legacy hooks before packages or downloads.
    if not configured:
        run(core)
    else:
        print('Desktop files already installed; preserving your desktop settings.')
    active = []
    missing = []
    for name in selected:
        exists = installed(tool, name)
        target, receipt = tool.paths(name)
        if exists and not receipt.exists():
            continue
        active.append(name)
        if not exists:
            missing.append(name)
    state_path = home / '.local/state/omarchy-mac-starter/setup.json'
    plugins.safe_path(home, state_path)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'backends': {}}
    pending = state.setdefault('plugins_pending', {})
    for name in missing:
        state['backends'].pop(name, None)
    first_activation = not configured or ('desktop' in journal.get('modules', []) and 'activation_pending' not in state)
    if first_activation and not sandbox:
        starter.remember_timer(home, run)
        state['activation_pending'] = True
        plugins.atomic_json(state_path, state)
    if not configured:
        run([*core, '--apply'])
    if not sandbox:
        packages = sorted({p for name in active for p in tool.module(name)['packages']})
        if packages:
            run(['omarchy', 'pkg', 'add', *packages])
    for name in active:
        if name not in missing and name not in pending:
            continue
        shadows = pending.get(name, all(
            (home / '.config/omarchy/ui/panel-shadows' / filename).is_file()
            for filename in ('KeyboardPanel.qml', 'PanelShadow.qml')))
        if not sandbox and name not in pending:
            pending[name] = shadows
            plugins.atomic_json(state_path, state)
        shadow_args = ['--with-shadows'] if shadows else []
        run([str(ROOT / 'plugins'), 'install', name, '--apply', *shadow_args, *home_args])
        if not sandbox:
            del pending[name]
            plugins.atomic_json(state_path, state)
    if sandbox:
        print('Staged only. Packages, backends, theme activation, and session reload were skipped.')
        return
    for name in active:
        backend(tool, name, state, state_path)
    if state.get('activation_pending'):
        if 'previous_theme' not in state:
            previous = home / '.local/state/omarchy/current/theme.name'
            state['previous_theme'] = previous.read_text().strip() if previous.is_file() else None
            plugins.atomic_json(state_path, state)
        run(['fc-cache', '-f'])
        run(['python3', str(home / starter.APPEARANCE), 'apply'])
        run(['systemctl', '--user', 'daemon-reload'])
        run(['systemctl', '--user', 'enable', '--now', starter.TIMER])
    run(['omarchy', 'restart', 'shell'])
    run(['hyprctl', 'reload'])
    errors = run(['hyprctl', 'configerrors'], capture=True)
    if errors:
        raise plugins.Refused('Hyprland reports configuration errors:\n' + errors)
    if state.get('activation_pending'):
        state['activation_pending'] = False
        plugins.atomic_json(state_path, state)
    print('Desktop installed. Configure accounts, devices, and plugin preferences in plugin settings.')
    if 'calendar' in active:
        print('Calendar is staged. Configure it, then enable it in plugin settings to replace the clock.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugins', nargs='*', metavar='NAME', help='optional plugin names; omit for core only with --yes')
    parser.add_argument('--yes', action='store_true', help='skip plugin selection and final confirmation')
    parser.add_argument('--dry-run', action='store_true', help='print a plan without running commands or writing files')
    parser.add_argument('--home', type=Path, help='stage into a separate home without changing the live session')
    args = parser.parse_args(argv)
    try:
        modules = plugins.load_modules(ROOT)
        home = (args.home or Path.home()).expanduser().resolve()
        if args.home is not None and home == Path.home().resolve():
            raise plugins.Refused('--home must name a separate staging home')
        selected = args.plugins
        if selected is None:
            selected = [] if args.yes or args.dry_run else choose(list(modules))
        selected = list(dict.fromkeys(selected))
        if any(name not in modules for name in selected):
            raise plugins.Refused('Unknown plugin. Choose from: ' + ', '.join(modules))
        print('Install desktop + shortcuts; optional plugins: ' + (', '.join(selected) or 'none'))
        print('Target home: ' + str(home))
        print('Preflight core conflicts, install core, then install selected pinned plugins and prerequisites.')
        if args.home is not None:
            print('Staging only; no package/backend/theme/reload commands.')
        else:
            print('Install Magic Mouse/AirPods backends and AirPlay service when selected; save prior theme,')
            print('refresh fonts, apply saved appearance, enable its timer, restart the shell and validate Hyprland.')
        print('Account login, pairing, remote Mac setup, and plugin preferences are yours to configure.')
        if 'calendar' in selected:
            print('Calendar stays staged until you configure and enable it in plugin settings.')
        if args.dry_run:
            return 0
        if not args.yes and input('Install this selection? [y/N] ').strip().lower() not in ('y', 'yes'):
            print('Cancelled.')
            return 0
        setup(home, selected, sandbox=args.home is not None)
        return 0
    except (plugins.Refused, starter.Conflict, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Error: {error}\nSetup did not finish. Resolve the error and rerun the same selection.', file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
