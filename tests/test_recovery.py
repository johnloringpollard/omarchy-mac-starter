"""Exercise durable installer mutations with a simulated stop before and after each write."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('starter_recovery', ROOT / 'scripts/starter.py')
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


class Interrupted(BaseException):
    pass


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / 'home'
        self.assets = self.base / 'repository'
        self.home.mkdir()
        self.original = {
            'bar': {
                'position': 'bottom', 'transparent': False,
                'centerAnchor': 'omarchy.clock',
                'layout': {
                    'left': [{'id': 'omarchy.menu'}],
                    'center': [{'id': 'omarchy.clock', 'format': 'HH:mm',
                                'formatAlt': 'yyyy-MM-dd', 'custom': {'timezone': 'UTC'}},
                               {'id': 'custom.weather', 'units': 'metric'}],
                    'right': [{'id': 'omarchy.audio', 'volumeStep': 3},
                              {'id': 'omarchy.network', 'showAddress': True}],
                },
            },
            'idle': {'lock': 321},
        }
        self.write(self.home / starter.HYPR, '-- original configuration\n')
        self.write(self.home / starter.SHELL, json.dumps(self.original))
        self.write(self.home / starter.TOML,
                   '# original style\n[font]\nbase-size = 11\n[popups]\nbackground-alpha = 0.9\n')
        for module in ('desktop', 'shortcuts'):
            self.write(self.assets / 'modules' / (module + '.lua'), '-- fixture ' + module + '\n')
        for name, value in {
            'theme/colors.toml': 'mode = "light"\n',
            'fonts/Inter.ttc': 'fixture font bytes',
            'apple-ui.conf': '<fontconfig/>\n',
            'panel-shadows/PanelShadow.qml': 'Item {}\n',
        }.items():
            self.write(self.assets / 'assets' / name, value)
        for name in ('audio', 'clock', 'network'):
            manifest = {'id': 'macstarter.' + name,
                        'omarchy': {'clonedFrom': 'omarchy.' + name}}
            self.write(self.assets / 'assets/plugins' / ('macstarter.' + name) / 'manifest.json',
                       json.dumps(manifest))
        self.root_patch = patch.object(starter, 'ROOT', self.assets)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def invoke(self, command):
        args = argparse.Namespace(command=command, home=self.home,
                                  apply=True, modules=['desktop', 'shortcuts'])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(starter.run(args), 0)

    def snapshot(self):
        return {str(path.relative_to(self.home)): path.read_bytes()
                for path in self.home.rglob('*') if path.is_file()}

    def restore(self, snapshot):
        shutil.rmtree(self.home)
        self.home.mkdir()
        for name, contents in snapshot.items():
            path = self.home / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)

    def shell(self):
        return json.loads((self.home / starter.SHELL).read_text())

    def durable_writes(self, command):
        events = []
        original_write = starter.Files.write

        def observe(fs, name, data):
            if fs.apply:
                events.append((name, 'delete' if data is None else 'replace'))
            return original_write(fs, name, data)

        with patch.object(starter.Files, 'write', observe):
            self.invoke(command)
        return events

    def interrupt(self, command, write_index, when):
        original_write = starter.Files.write
        seen = 0

        def interrupted_write(fs, name, data):
            nonlocal seen
            if not fs.apply:
                return original_write(fs, name, data)
            current = seen
            seen += 1
            if current == write_index and when == 'before':
                raise Interrupted()
            result = original_write(fs, name, data)
            if current == write_index and when == 'after':
                raise Interrupted()
            return result

        with patch.object(starter.Files, 'write', interrupted_write):
            with self.assertRaises(Interrupted):
                self.invoke(command)
        self.assertEqual(seen, write_index + 1)

    def assert_installed(self, expected):
        observed = {name: contents for name, contents in self.snapshot().items()
                    if not name.startswith(starter.STATE + '/')}
        self.assertEqual(observed, expected)
        journal = json.loads((self.home / starter.STATE / 'journal.json').read_text())
        self.assertEqual(journal['status'], 'installed')
        clock = self.shell()['bar']['layout']['right'][-1]
        self.assertEqual(clock['id'], 'macstarter.clock')
        self.assertEqual(clock['format'], 'dddd h:mm AP')
        self.assertEqual(clock['custom'], {'timezone': 'UTC'})
        self.invoke('doctor')

    def test_install_recovers_at_every_durable_write_boundary(self):
        baseline = self.snapshot()
        events = self.durable_writes('install')
        expected = {name: contents for name, contents in self.snapshot().items()
                    if not name.startswith(starter.STATE + '/')}
        self.assertTrue(any(name.endswith('/progress.json') for name, _ in events))
        self.assertGreater(sum(name == starter.SHELL for name, _ in events), 6)
        for index, event in enumerate(events):
            for when in ('before', 'after'):
                with self.subTest(write=index, event=event, when=when):
                    self.restore(baseline)
                    self.interrupt('install', index, when)
                    self.invoke('install')
                    self.assert_installed(expected)
                    self.invoke('install')
                    self.assert_installed(expected)

    def test_uninstall_recovers_at_every_durable_write_boundary(self):
        self.invoke('install')
        data = self.shell()
        data['bar']['layout']['right'][-1]['custom'] = {'timezone': 'Europe/Paris'}
        data['bar']['layout']['right'][0]['volumeStep'] = 7
        data['bar']['layout']['right'].append({'id': 'custom.new', 'enabled': True})
        data['idle']['lock'] = 999
        self.write(self.home / starter.SHELL, json.dumps(data))
        with (self.home / starter.HYPR).open('a') as stream:
            stream.write('-- added after install\n')
        with (self.home / starter.TOML).open('a') as stream:
            stream.write('border-width = 7\n')
        baseline = self.snapshot()
        events = self.durable_writes('uninstall')
        expected = copy.deepcopy(self.original)
        expected['bar']['layout']['center'][0]['custom'] = {'timezone': 'Europe/Paris'}
        expected['bar']['layout']['right'][0]['volumeStep'] = 7
        expected['bar']['layout']['right'].append({'id': 'custom.new', 'enabled': True})
        expected['idle']['lock'] = 999
        for index, event in enumerate(events):
            for when in ('before', 'after'):
                with self.subTest(write=index, event=event, when=when):
                    self.restore(baseline)
                    self.interrupt('uninstall', index, when)
                    self.invoke('uninstall')
                    self.assertEqual(self.shell(), expected)
                    self.assertEqual((self.home / starter.HYPR).read_text(),
                                     '-- original configuration\n-- added after install\n')
                    style = tomllib.loads((self.home / starter.TOML).read_text())
                    self.assertEqual(style['font']['base-size'], 11)
                    self.assertEqual(style['popups'], {'background-alpha': 0.9, 'border-width': 7})
                    self.assertFalse((self.home / starter.STATE / 'journal.json').exists())
                    self.assertFalse((self.home / starter.STATE / 'progress.json').exists())
                    owned = [name for name in self.snapshot()
                             if name not in (starter.HYPR, starter.SHELL, starter.TOML)
                             and not name.startswith(starter.STATE + '/')]
                    self.assertEqual(owned, [])
                    self.invoke('uninstall')
                    self.assertEqual(self.shell(), expected)

    def test_repeat_install_resets_old_progress_before_replaying(self):
        self.invoke('install')
        expected = {name: contents for name, contents in self.snapshot().items()
                    if not name.startswith(starter.STATE + '/')}
        data = self.shell()
        data['bar']['position'] = 'bottom'
        self.write(self.home / starter.SHELL, json.dumps(data))
        baseline = self.snapshot()
        events = self.durable_writes('install')
        for index, event in enumerate(events):
            for when in ('before', 'after'):
                with self.subTest(write=index, event=event, when=when):
                    self.restore(baseline)
                    self.interrupt('install', index, when)
                    self.invoke('install')
                    self.assert_installed(expected)



if __name__ == '__main__':
    unittest.main()
