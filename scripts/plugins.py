#!/usr/bin/env python3
"""Fetch and install reviewed plugin revisions without exporting personal state."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


class Refused(Exception):
    pass


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True, timeout=300).stdout.strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(home, path):
    current = home
    for part in path.relative_to(home).parts:
        current /= part
        if current.is_symlink():
            raise Refused(f'Refusing a symlink in a managed path: {current}')


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, indent=2)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def tree(path):
    result = {}
    for item in sorted(path.rglob('*')):
        relative = item.relative_to(path)
        if '.git' in relative.parts:
            continue
        if item.is_symlink():
            result[str(relative)] = ['link', os.readlink(item)]
        elif item.is_file():
            result[str(relative)] = ['file', digest(item.read_bytes()), item.stat().st_mode & 0o777]
    return result


def git_refs(path):
    return run(['git', '-C', str(path), 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads', 'refs/stash'])


def load_modules(root=ROOT):
    document = json.loads((root / 'dependencies.lock.json').read_text())
    if document.get('schema') != 1:
        raise Refused('Unsupported dependency lock schema')
    modules = document['modules']
    for name, module in modules.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', name):
            raise Refused('Invalid module name')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', module['id']):
            raise Refused('Invalid plugin ID')
        if not re.fullmatch(r'[0-9a-f]{40}', module['commit']):
            raise Refused(f'{name}: expected a full Git commit')
        if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', module['url']):
            raise Refused(f'{name}: expected a public GitHub URL')
        for patch in module['patches']:
            path = root / patch['path']
            if path.is_symlink() or not path.resolve().is_relative_to((root / 'patches').resolve()):
                raise Refused('Patch must be a regular file inside patches/')
            if digest(path.read_bytes()) != patch['sha256']:
                raise Refused(f'Patch checksum mismatch: {patch["path"]}')
    return modules


@contextlib.contextmanager
def lock(home):
    state = home / '.local/state/omarchy-mac-starter'
    safe_path(home, state / 'operation.lock')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'operation.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


class Plugins:
    def __init__(self, home, root=ROOT, sandbox=False):
        self.home = home
        self.root = root
        self.sandbox = sandbox
        self.modules = load_modules(root)

    def module(self, name):
        if name not in self.modules:
            raise Refused(f'Unknown module: {name}')
        return self.modules[name]

    def paths(self, name):
        module = self.module(name)
        return (self.home / '.config/omarchy/plugins' / module['id'],
                self.home / '.local/state/omarchy-mac-starter/plugins' / f'{name}.json')

    def patches(self, module, shadows):
        return [p for p in module['patches'] if p['kind'] != 'shadows' or shadows]

    def cache_paths(self, name, shadows):
        module = self.module(name)
        key = digest(json.dumps([module['commit'], self.patches(module, shadows)], sort_keys=True).encode())[:16]
        base = self.home / '.cache/omarchy-mac-starter/plugins'
        return base / f'{name}-{key}', base / f'{name}-{key}.json'

    def verify(self, target, expected, module, refs):
        if target.is_symlink() or not target.is_dir():
            raise Refused(f'Expected an owned checkout: {target}')
        if run(['git', '-C', str(target), 'rev-parse', 'HEAD']) != module['commit']:
            raise Refused(f'Git revision changed: {target}')
        if tree(target) != expected:
            raise Refused(f'Checkout has changed; preserve or move it manually: {target}')
        if git_refs(target) != refs:
            raise Refused(f'Local branches or stashes changed; preserve them before removal: {target}')

    def fetch(self, name, shadows=False):
        module = self.module(name)
        target, receipt = self.cache_paths(name, shadows)
        safe_path(self.home, target)
        safe_path(self.home, receipt)
        if target.exists() or target.is_symlink():
            if not receipt.is_file():
                raise Refused(f'Unmanaged cache exists: {target}')
            saved = json.loads(receipt.read_text())
            self.verify(target, saved['files'], module, saved['refs'])
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.fetch-', dir=target.parent) as temporary:
            checkout = Path(temporary) / 'checkout'
            print(f'Fetch {name} at {module["commit"]}', flush=True)
            run(['git', 'clone', '--no-checkout', '--filter=blob:none', '--', module['url'], str(checkout)])
            run(['git', '-C', str(checkout), 'checkout', '--detach', module['commit']])
            for patch in self.patches(module, shadows):
                run(['git', '-C', str(checkout), 'apply', '--check', str(self.root / patch['path'])])
                run(['git', '-C', str(checkout), 'apply', str(self.root / patch['path'])])
            manifest = json.loads((checkout / 'manifest.json').read_text())
            if manifest.get('id') != module['id']:
                raise Refused('Fetched plugin identity differs from dependency lock')
            expected = tree(checkout)
            atomic_json(receipt, {'files': expected, 'commit': module['commit'], 'refs': git_refs(checkout)})
            checkout.rename(target)
        return target

    def describe(self, name):
        module = self.module(name)
        print(f'{name}: {module["id"]} {module["version"]} @ {module["commit"]}')
        if module['packages']:
            print('Package prerequisites: ' + ' '.join(module['packages']))
        if module['setup']:
            target, _ = self.paths(name)
            print(f'After installation, read docs/devices.md, then run in {target}:')
            print('  ' + shlex.join(module['setup']))
        else:
            print('See docs/devices.md for dependencies and account/device setup.')

    def install(self, name, apply=False, shadows=False):
        module = self.module(name)
        shadows = shadows and any(p['kind'] == 'shadows' for p in module['patches'])
        target, receipt = self.paths(name)
        print(f'Install pinned {name} to {target}')
        self.describe(name)
        if not apply:
            print('Preview only. Add --apply to fetch, install, and enable the widget.')
            return
        safe_path(self.home, target)
        safe_path(self.home, receipt)
        if not self.sandbox and not shutil.which('omarchy'):
            raise Refused('Omarchy is required to enable plugins')
        if shadows and any(p['kind'] == 'shadows' for p in module['patches']):
            for filename in ('KeyboardPanel.qml', 'PanelShadow.qml'):
                if not (self.home / '.config/omarchy/ui/panel-shadows' / filename).is_file():
                    raise Refused('Install the desktop module before --with-shadows')
        cache = self.fetch(name, shadows)
        expected = tree(cache)
        state = {'module': name, 'commit': module['commit'], 'shadows': shadows, 'files': expected, 'refs': git_refs(cache)}
        if receipt.exists():
            saved = json.loads(receipt.read_text())
            if saved != state:
                raise Refused('Installed selection differs; remove it before selecting another variant')
        elif target.exists() or target.is_symlink():
            raise Refused(f'Existing plugin is not owned by this starter: {target}')
        if target.exists() or target.is_symlink():
            self.verify(target, expected, module, state['refs'])
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_json(receipt, state)
            with tempfile.TemporaryDirectory(prefix='.install-', dir=target.parent) as temporary:
                staged = Path(temporary) / 'checkout'
                shutil.copytree(cache, staged, symlinks=True)
                staged.rename(target)
        if self.sandbox:
            print('Alternate home: staged files only; no live shell commands executed.')
        else:
            run(['omarchy', 'plugin', 'validate', str(target)])
            run(['omarchy-shell', 'shell', 'rescanPlugins'])
            deadline = time.monotonic() + 5
            while True:
                known = json.loads(run(['omarchy', 'plugin', 'list', '--json']))
                if any(item['id'] == module['id'] for item in known):
                    break
                if time.monotonic() >= deadline:
                    raise Refused('Plugin discovery timed out; source is saved, retry installation to enable it')
                time.sleep(0.15)
            # OmaCal replaces a clock; changing an existing clock requires the
            # field-aware desktop installer, rather than disabling a fixed ID.
            if name == 'calendar':
                print('OmaCal is staged. Follow docs/devices.md to replace your current clock.')
            else:
                run(['omarchy', 'plugin', 'enable', module['id']])
        print('Plugin source installed. Backend/package setup is a separate explicit step.')

    def remove(self, name, apply=False):
        module = self.module(name)
        target, receipt = self.paths(name)
        safe_path(self.home, target)
        safe_path(self.home, receipt)
        if not receipt.exists():
            if not target.exists():
                print(f'{name}: nothing installed by this starter')
                return
            raise Refused(f'No starter install record for {name}')
        saved = json.loads(receipt.read_text())
        if target.exists() or target.is_symlink():
            self.verify(target, saved['files'], module, saved['refs'])
        print(f'Remove owned plugin source: {target}')
        print('This does not uninstall daemons, packages, device rules, or account data. See docs/devices.md.')
        if not apply:
            print('Preview only. Add --apply after completing any backend removal.')
            return
        if not self.sandbox and target.exists():
            shell = self.home / '.config/omarchy/shell.json'
            if shell.is_file():
                config = json.loads(shell.read_text())
                widgets = [widget for group in config.get('bar', {}).get('layout', {}).values()
                           for widget in group if widget.get('id') == module['id']]
                backup = receipt.with_name(f'{name}-widget-backup-{time.time_ns()}.json')
                atomic_json(backup, {'id': module['id'], 'widgets': widgets})
            run(['omarchy', 'plugin', 'disable', module['id']])
        if target.exists():
            shutil.rmtree(target)
        receipt.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'fetch', 'install', 'remove'])
    parser.add_argument('module', nargs='?')
    parser.add_argument('--apply', action='store_true', help='apply install/removal; otherwise preview')
    parser.add_argument('--with-shadows', action='store_true', help='include optional shared-panel styling patches')
    parser.add_argument('--home', type=Path, help='stage in another home; never call the live Omarchy shell')
    args = parser.parse_args(argv)
    home = (args.home or Path.home()).expanduser().resolve()
    sandbox = args.home is not None
    if sandbox and home == Path.home().resolve():
        parser.error('--home must name a separate test home, not your real home')
    try:
        plugins = Plugins(home, sandbox=sandbox)
        if args.action == 'list':
            for name in plugins.modules:
                plugins.describe(name)
            return 0
        if not args.module:
            parser.error('module is required')
        plugins.module(args.module)
        changing = args.action == 'fetch' or args.apply
        with lock(home) if changing else contextlib.nullcontext():
            if args.action == 'fetch':
                print(plugins.fetch(args.module, args.with_shadows))
            elif args.action == 'install':
                plugins.install(args.module, args.apply, args.with_shadows)
            else:
                plugins.remove(args.module, args.apply)
        return 0
    except (Refused, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Error: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.strip(), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
