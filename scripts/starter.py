#!/usr/bin/env python3
"""Scoped, journaled Omarchy configuration installer."""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import subprocess
import tempfile
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]
STATE = '.local/state/omarchy-mac-starter'
SHELL = '.config/omarchy/shell.json'
TOML = '.config/omarchy/shell.toml'
HYPR = '.config/hypr/hyprland.lua'
ABSENT = {'absent': True}
APPEARANCE = '.local/bin/mac-starter-appearance'
TIMER = 'mac-starter-appearance.timer'
TIMER_STATE = STATE + '/appearance-timer.json'


class Conflict(Exception):
    pass


def encoded(data):
    return ABSENT if data is None else base64.b64encode(data).decode('ascii')


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.mac-starter-', dir=path.parent)
    try:
        if path.exists():
            os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Files:
    def __init__(self, home, apply=False):
        self.home = home.resolve()
        self.apply = apply
        self.cache = {}

    def path(self, name):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise Conflict(f'Unsafe relative path: {name}')
        path = self.home / relative
        for candidate in (path, *path.parents):
            if candidate == self.home:
                break
            if candidate.is_symlink():
                raise Conflict(f'Refusing symlink: {candidate}')
        return path

    def read(self, name):
        path = self.path(name)
        if name not in self.cache:
            self.cache[name] = path.read_bytes() if path.exists() else None
        return self.cache[name]

    def write(self, name, data):
        path = self.path(name)
        if self.apply:
            if data is None:
                path.unlink(missing_ok=True)
            else:
                atomic(path, data)
        self.cache[name] = data

    def json(self, name):
        return json.loads(self.read(name) or b'{}')


def layout(data):
    result = data.get('bar', {}).get('layout', {})
    for section, widgets in result.items():
        if section not in ('left', 'center', 'right') or not isinstance(widgets, list):
            raise Conflict('Unsupported bar layout')
        ids = [widget.get('id') for widget in widgets]
        if not all(isinstance(identifier, str) for identifier in ids):
            raise Conflict('Each widget must have a string id')
    all_ids = [widget['id'] for widgets in result.values() for widget in widgets]
    if len(all_ids) != len(set(all_ids)):
        raise Conflict('Duplicate widget ids in bar layout')
    return result


def find_widget(data, identifier):
    for section, widgets in layout(data).items():
        for index, widget in enumerate(widgets):
            if widget['id'] == identifier:
                return section, index, widget
    return None


def field(data, keys, value=None, write=False):
    current = data
    for key in keys[:-1]:
        if key not in current:
            if not write or value == ABSENT:
                return ABSENT
            current[key] = {}
        current = current[key]
        if not isinstance(current, dict):
            raise Conflict(f'Expected object at {key}')
    if write:
        if value == ABSENT:
            current.pop(keys[-1], None)
        else:
            current[keys[-1]] = value
    return current.get(keys[-1], ABSENT)


def toml_value(text, section, key, value=None, write=False):
    parsed = tomllib.loads(text)
    current = parsed.get(section, {}).get(key, ABSENT)
    if not write:
        return current
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if re.fullmatch(r'\s*\[' + re.escape(section) + r'\]\s*(?:#.*)?\n?', line)), None)
    if start is None:
        if section in parsed:
            raise Conflict(f'Unsupported TOML section spelling: {section}')
        if value == ABSENT:
            return text
        lines += [('\n' if text and not text.endswith('\n') else '') + f'\n[{section}]\n']
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].lstrip().startswith('[')), len(lines))
    index = next((i for i in range(start + 1, end)
                  if re.match(r'\s*' + re.escape(key) + r'\s*=', lines[i])), None)
    if index is None and current != ABSENT:
        raise Conflict(f'Unsupported TOML key spelling: {section}.{key}')
    if index is not None:
        lines[index:index + 1] = [] if value == ABSENT else [f'{key} = {json.dumps(value)}\n']
    elif value != ABSENT:
        lines.insert(end, f'{key} = {json.dumps(value)}\n')
    result = ''.join(lines)
    tomllib.loads(result)
    return result


def operate(fs, operation, value=None, write=False):
    name, kind = operation['path'], operation['kind']
    raw = fs.read(name)
    if kind == 'file':
        current = encoded(raw)
        if write:
            fs.write(name, None if value == ABSENT else base64.b64decode(value))
        return current
    if kind == 'block':
        text = (raw or b'').decode()
        begin = '-- BEGIN mac-starter ' + operation['module']
        end = '-- END mac-starter ' + operation['module']
        pattern = re.compile(re.escape(begin) + r'\n.*?' + re.escape(end) + r'\n?', re.S)
        matches = list(pattern.finditer(text))
        if len(matches) > 1 or text.count(begin) != len(matches) or text.count(end) != len(matches):
            raise Conflict(f'Malformed managed block in {name}')
        current = matches[0].group() if matches else ABSENT
        if write:
            replacement = '' if value == ABSENT else value
            if matches:
                text = text[:matches[0].start()] + replacement + text[matches[0].end():]
            elif replacement:
                text += ('\n' if text and not text.endswith('\n') else '') + replacement
            fs.write(name, text.encode())
        return current
    if kind == 'toml':
        text = (raw or b'').decode()
        result = toml_value(text, operation['section'], operation['key'], value, write)
        if write:
            fs.write(name, result.encode())
        return result
    data = fs.json(name)
    if kind == 'json':
        current = field(data, operation['keys'], value, write)
    elif kind == 'rename':
        old = find_widget(data, operation['id'])
        new = find_widget(data, operation['replacement'])
        if bool(old) == bool(new):
            raise Conflict(f'Expected exactly one of {operation["id"]} and {operation["replacement"]}')
        widget = (old or new)[2]
        current = widget['id']
        if write:
            widget['id'] = value
    else:
        found = find_widget(data, operation['id'])
        if kind == 'widget':
            if not found:
                raise Conflict(f'Widget removed: {operation["id"]}')
            current = field(found[2], [operation['key']], value, write)
        elif kind == 'insert':
            current = found[2] if found else ABSENT
            if write:
                if found:
                    del layout(data)[found[0]][found[1]]
                if value != ABSENT:
                    data.setdefault('bar', {}).setdefault('layout', {}).setdefault('right', []).append(value)
        elif kind == 'move':
            if not found:
                raise Conflict(f'Widget removed: {operation["id"]}')
            known = set(operation['known'])
            current = {'section': found[0], 'order': [w['id'] for w in layout(data)[found[0]] if w['id'] in known]}
            if write:
                widget = layout(data)[found[0]].pop(found[1])
                target = layout(data).setdefault(value['section'], [])
                desired = value['order']
                index = desired.index(operation['id'])
                following = desired[index + 1:]
                insertion = next((i for i, item in enumerate(target) if item['id'] in following), len(target))
                target.insert(insertion, widget)
        else:
            raise Conflict(f'Unknown journal operation: {kind}')
    if write:
        fs.write(name, (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode())
    return current


def timer_command(command, capture=False):
    result = subprocess.run(command, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return (result.stdout or '').strip()


def remember_timer(home, runner=timer_command):
    fs = Files(home, apply=True)
    if fs.read(TIMER_STATE):
        return
    values = []
    for query in ('is-enabled', 'is-active'):
        try:
            value = runner(['systemctl', '--user', query, TIMER], capture=True)
        except subprocess.CalledProcessError as error:
            value = (error.stdout or '').strip()
        values.append(value)
    enabled, active = values
    if enabled not in ('enabled', 'enabled-runtime', 'disabled', 'not-found') or active not in ('active', 'inactive', 'failed', 'unknown'):
        raise Conflict(f'Cannot manage appearance timer with state {enabled!r}, {active!r}')
    fs.write(TIMER_STATE, (json.dumps({'enabled': enabled, 'active': active == 'active'}) + '\n').encode())


def stop_appearance_jobs():
    for action, unit in [('disable', TIMER), ('stop', 'mac-starter-appearance.service')]:
        command = ['systemctl', '--user', action]
        if action == 'disable':
            command.append('--now')
        try:
            timer_command([*command, unit])
        except subprocess.CalledProcessError:
            loaded = timer_command(['systemctl', '--user', 'show', '--property=LoadState', '--value', unit], capture=True)
            if loaded != 'not-found':
                raise


def restore_timer(home):
    fs = Files(home, apply=True)
    prior = fs.json(TIMER_STATE)
    timer_command(['systemctl', '--user', 'daemon-reload'])
    if prior.get('enabled') in ('enabled', 'enabled-runtime'):
        command = ['systemctl', '--user', 'enable']
        if prior['enabled'] == 'enabled-runtime':
            command.append('--runtime')
        timer_command([*command, TIMER])
    if prior.get('active'):
        timer_command(['systemctl', '--user', 'start', TIMER])


def plan(fs, modules):
    if not fs.read(HYPR) or not fs.read(SHELL):
        raise Conflict('Expected an existing Lua-based Omarchy installation: hyprland.lua and shell.json are required')
    operations = []

    def add(kind, path, after, **metadata):
        operation = dict(kind=kind, path=path, **metadata)
        before = operate(fs, operation)
        if before == after:
            return
        if kind == 'file' and before != ABSENT:
            raise Conflict(f'Existing unmanaged file: {path}')
        operation.update(before=before, after=after)
        operate(fs, operation, after, True)
        operations.append(operation)

    for module in modules:
        destination = f'.config/hypr/mac-starter/{module}.lua'
        add('file', destination, encoded((ROOT / 'modules' / f'{module}.lua').read_bytes()))
        block = (f'-- BEGIN mac-starter {module}\n'
                 f'dofile(os.getenv("HOME") .. "/{destination}")\n'
                 f'-- END mac-starter {module}\n')
        add('block', HYPR, block, module=module)
    if 'desktop' in modules:
        if fs.read('.config/omarchy/hooks/theme-set.d/apple-desktop') and fs.read('.local/state/omarchy/apple/active.json'):
            raise Conflict('Legacy Apple theme restore hook detected. Follow docs/migration.md before installing.')
        for directory, slug in [('theme', 'mac-starter'), ('theme-dark', 'mac-starter-dark')]:
            for source in sorted((ROOT / 'assets' / directory).rglob('*')):
                if source.is_file():
                    add('file', f'.config/omarchy/themes/{slug}/' + str(source.relative_to(ROOT / 'assets' / directory)), encoded(source.read_bytes()))
        for filename, destination in [
            ('mac-starter-appearance', APPEARANCE),
            ('mac-starter-appearance.service', '.config/systemd/user/mac-starter-appearance.service'),
            (TIMER, '.config/systemd/user/' + TIMER),
            ('mac-starter-appearance.desktop', '.local/share/applications/mac-starter-appearance.desktop'),
        ]:
            add('file', destination, encoded((ROOT / 'assets/appearance' / filename).read_bytes()))
        for source in sorted((ROOT / 'assets/fonts').iterdir()):
            add('file', '.local/share/fonts/mac-starter/' + source.name, encoded(source.read_bytes()))
        add('file', '.config/fontconfig/conf.d/99-mac-starter.conf', encoded((ROOT / 'assets/apple-ui.conf').read_bytes()))
        for source in sorted((ROOT / 'assets/panel-shadows').glob('*.qml')):
            add('file', '.config/omarchy/ui/panel-shadows/' + source.name, encoded(source.read_bytes()))
        for source in sorted((ROOT / 'assets/plugins').rglob('*')):
            if source.is_file():
                destination = '.config/omarchy/plugins/' + str(source.relative_to(ROOT / 'assets/plugins'))
                add('file', destination, encoded(source.read_bytes()))
        data = fs.json(SHELL)
        for manifest in sorted((ROOT / 'assets/plugins').glob('*/manifest.json')):
            plugin = json.loads(manifest.read_text())
            original = plugin['omarchy']['clonedFrom']
            if find_widget(data, original):
                add('rename', SHELL, plugin['id'], id=original, replacement=plugin['id'])
        for section, key, value in [('font', 'base-size', 13), ('popups', 'background', ABSENT), ('popups', 'background-alpha', ABSENT)]:
            add('toml', TOML, value, section=section, key=key)
        for keys, value in [(['bar', 'position'], 'top'), (['bar', 'transparent'], True), (['bar', 'centerAnchor'], '')]:
            add('json', SHELL, value, keys=keys)
        data = fs.json(SHELL)
        widgets = [w for items in layout(data).values() for w in items]
        def is_clock(widget):
            identifier = widget['id']
            if identifier == 'crmne.omacal' or identifier.endswith('.clock'):
                return True
            manifest = fs.json(f'.config/omarchy/plugins/{identifier}/manifest.json')
            return manifest.get('omarchy', {}).get('clonedFrom') == 'omarchy.clock'

        clocks = [w for w in widgets if is_clock(w)]
        if len(clocks) > 1:
            raise Conflict('Multiple clocks found; choose one in shell.json before installing')
        if clocks:
            identifier = clocks[0]['id']
            add('widget', SHELL, 'dddd h:mm AP', id=identifier, key='format')
            add('widget', SHELL, 'dddd, MMMM d, yyyy', id=identifier, key='formatAlt')
            data = fs.json(SHELL)
            section, index, widget = find_widget(data, identifier)
            known = [w['id'] for items in layout(data).values() for w in items]
            desired = [w['id'] for w in layout(data).get('right', []) if w['id'] != identifier] + [identifier]
            add('move', SHELL, {'section': 'right', 'order': desired}, id=identifier, known=known)
        else:
            add('insert', SHELL, {'id': 'macstarter.clock', 'format': 'dddd h:mm AP',
                                 'formatAlt': 'dddd, MMMM d, yyyy'}, id='macstarter.clock')
    return operations


def run(args):
    home = args.home.expanduser().resolve()
    fs = Files(home)
    journal_name = STATE + '/journal.json'
    progress_name = STATE + '/progress.json'
    journal_raw = fs.read(journal_name)
    journal = json.loads(journal_raw) if journal_raw else None
    if journal and (journal.get('version') != 1 or journal.get('home') != str(home)):
        raise Conflict('Journal version or home does not match')
    if args.command == 'doctor':
        for name in (HYPR, SHELL):
            print(f'{name}: {"present" if fs.read(name) else "MISSING"}')
        if fs.read(SHELL):
            layout(fs.json(SHELL))
        tomllib.loads((fs.read(TOML) or b'').decode())
        conflicts = []
        for operation in journal['operations'] if journal else []:
            try:
                if operate(fs, operation) != operation['after']:
                    conflicts.append(operation['path'])
            except Conflict as error:
                conflicts.append(str(error))
        print(f'Journal: {journal["status"] if journal else "not installed"}')
        for name in conflicts:
            print(f'Changed: {name}')
        print('Session reload and rendered appearance are not checked. No subprocesses are run.')
        return 1 if conflicts or not fs.read(HYPR) or not fs.read(SHELL) else 0
    uninstall = args.command == 'uninstall'
    if uninstall and not journal:
        if args.apply:
            if home == Path.home().resolve() and fs.read(TIMER_STATE):
                restore_timer(home)
                Files(home, apply=True).write(TIMER_STATE, None)
            Files(home, apply=True).write(progress_name, None)
        print('Nothing installed.')
        return 0
    if uninstall and 'desktop' in journal['modules']:
        current_theme = (fs.read('.local/state/omarchy/current/theme.name') or b'').decode().strip()
        if current_theme in ('mac-starter', 'mac-starter-dark'):
            raise Conflict('Switch to another theme before uninstalling the Mac starter desktop')
    if uninstall and any(op['path'].startswith('.config/omarchy/ui/panel-shadows/')
                         and op['before'] == ABSENT for op in journal['operations']):
        receipts = fs.path(STATE + '/plugins')
        for receipt in receipts.glob('*.json'):
            if json.loads(receipt.read_text()).get('shadows'):
                raise Conflict(f'Remove the shadow-enabled plugin {receipt.stem} before uninstalling the desktop')
    if not uninstall:
        modules = sorted(set(args.modules))
        if journal:
            if journal['modules'] != modules or journal['status'] == 'removing':
                raise Conflict('Uninstall the previous selection before changing modules or resuming installation')
        else:
            operations = plan(fs, modules)
            journal = {'version': 1, 'generation': uuid.uuid4().hex, 'home': str(home),
                       'modules': modules, 'status': 'installing', 'operations': operations}
    operations = list(reversed(journal['operations'])) if uninstall else journal['operations']
    phase = 'removing' if uninstall else 'installing'
    progress = fs.json(progress_name)
    completed = (progress.get('completed', 0) if journal['status'] == phase
                 and progress.get('phase') == phase
                 and progress.get('generation') == journal.get('generation') else 0)
    if not isinstance(completed, int) or not 0 <= completed <= len(operations):
        raise Conflict('Invalid journal progress')
    remaining = operations[completed:]
    check = Files(home)
    conflicts = []
    for operation in remaining:
        current = operate(check, operation)
        expected, target = (operation['after'], operation['before']) if uninstall else (operation['before'], operation['after'])
        if current != target and current != expected:
            conflicts.append(f'{operation["path"]} ({operation["kind"]})')
        elif current != target:
            operate(check, operation, target, True)
    if conflicts:
        raise Conflict('Preserved edits; resolve conflicts before retrying:\n  ' + '\n  '.join(conflicts))
    for operation in remaining:
        print(f'{"Restore" if uninstall else "Set"} {operation["path"]} [{operation["kind"]}]')
    if not args.apply:
        print('Preview only. Repeat with --apply to write these changes.')
        return 0
    fs = Files(home, apply=True)
    manage_timer = uninstall and home == Path.home().resolve() and (
        fs.read(TIMER_STATE) is not None or any(op['path'] == '.config/systemd/user/' + TIMER for op in journal['operations']))
    if manage_timer:
        stop_appearance_jobs()
        current_theme = (Files(home).read('.local/state/omarchy/current/theme.name') or b'').decode().strip()
        if current_theme in ('mac-starter', 'mac-starter-dark'):
            raise Conflict('Appearance changed while stopping its jobs. Switch to another theme before uninstalling.')
    if journal['status'] != phase:
        fs.write(progress_name, (json.dumps({'generation': journal.get('generation'),
                 'phase': phase, 'completed': 0}) + '\n').encode())
    journal['status'] = phase
    fs.write(journal_name, (json.dumps(journal, indent=2) + '\n').encode())
    for index, operation in enumerate(remaining, start=completed + 1):
        current = operate(fs, operation)
        expected, target = (operation['after'], operation['before']) if uninstall else (operation['before'], operation['after'])
        if current not in (expected, target):
            raise Conflict(f'Configuration changed during apply: {operation["path"]}')
        if current != target:
            operate(fs, operation, target, True)
        fs.write(progress_name, (json.dumps({'generation': journal.get('generation'),
                 'phase': phase, 'completed': index}) + '\n').encode())
    if uninstall:
        if manage_timer:
            restore_timer(home)
        fs.write(journal_name, None)
        if manage_timer:
            fs.write(TIMER_STATE, None)
        fs.write(progress_name, None)
        print('Uninstalled. Unrelated settings are preserved; empty directories may remain.')
    else:
        journal['status'] = 'installed'
        fs.write(journal_name, (json.dumps(journal, indent=2) + '\n').encode())
        print('Installed. No theme command or session reload was run.')
        if 'desktop' in journal['modules']:
            print('To activate appearance and its timer, run ./setup --yes')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall', 'doctor'])
    parser.add_argument('--home', type=Path, help='stage into a separate home without changing the live session')
    parser.add_argument('--apply', action='store_true', help='Write changes; otherwise preview only')
    parser.add_argument('--modules', nargs='+', choices=['desktop', 'shortcuts'], default=['desktop', 'shortcuts'])
    args = parser.parse_args()
    try:
        if args.home is not None and args.home.expanduser().resolve() == Path.home().resolve():
            raise Conflict('--home must name a separate staging home')
        args.home = args.home or Path.home()
        if args.apply and args.command != 'doctor':
            fs = Files(args.home)
            lock_path = fs.path(STATE + '/operation.lock')
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return run(args)
        return run(args)
    except (Conflict, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
