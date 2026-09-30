import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
SPEC = importlib.util.spec_from_file_location('starter_setup', ROOT / 'scripts/setup.py')
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / 'home'
        self.tool = setup.plugins.Plugins(self.home)
        self.commands = []
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        self.mock = patch.object(setup, 'run', side_effect=self.run_command)
        self.runner = self.mock.start()
        self.addCleanup(self.mock.stop)

    def run_command(self, command, cwd=None, capture=False):
        self.commands.append((command, cwd))
        if command[0] == 'git':
            return self.tool.modules[self.selected]['commit']
        if command[:2] == [str(ROOT / 'plugins'), 'install']:
            self.owned(command[2])
        return ''

    def owned(self, name):
        module = self.tool.modules[name]
        target, receipt = self.tool.paths(name)
        target.mkdir(parents=True, exist_ok=True)
        files = {}
        if module['setup']:
            script = target / module['setup'][1]
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text('echo backend\n')
            files[module['setup'][1]] = ['file', setup.plugins.digest(script.read_bytes()), script.stat().st_mode & 0o777]
        setup.plugins.atomic_json(receipt, {'module': name, 'commit': module['commit'],
            'shadows': any(p['kind'] == 'shadows' for p in module['patches']), 'files': files})
        return target, receipt

    def test_dry_run_never_prompts_executes_or_writes(self):
        with patch.object(setup.subprocess, 'run', side_effect=AssertionError('subprocess')), patch('builtins.input', side_effect=AssertionError('prompt')):
            self.assertEqual(setup.main(['--dry-run', '--home', str(self.home), '--plugins', 'airpods']), 0)
        self.assertEqual(self.commands, [])
        self.assertFalse(self.home.exists())

    def test_yes_defaults_to_core_and_activation_order(self):
        with patch.object(setup.Path, 'home', return_value=self.home), patch('builtins.input', side_effect=AssertionError('prompt')):
            self.assertEqual(setup.main(['--yes']), 0)
        self.assertEqual([c for c, _ in self.commands], [[str(ROOT / 'install')], [str(ROOT / 'install'), '--apply'],
            ['fc-cache', '-f'], ['omarchy', 'theme', 'set', 'mac-starter'], ['omarchy', 'restart', 'shell'],
            ['hyprctl', 'reload'], ['hyprctl', 'configerrors']])

    def test_staging_runs_only_core_and_plugin_clis(self):
        setup.setup(self.home, list(self.tool.modules), sandbox=True)
        self.assertTrue(all(c[0] in (str(ROOT / 'install'), str(ROOT / 'plugins')) for c, _ in self.commands))
        self.assertTrue(all(c[-2:] == ['--home', str(self.home)] or '--home' in c for c, _ in self.commands))
        self.assertFalse((self.home / '.local/state/omarchy-mac-starter/setup.json').exists())

    def test_conflict_stops_before_any_mutation(self):
        self.runner.side_effect = subprocess.CalledProcessError(1, ['install'])
        with self.assertRaises(subprocess.CalledProcessError):
            setup.setup(self.home, ['airpods'])
        self.assertEqual(self.runner.call_count, 1)
        self.assertFalse(self.home.exists())

    def test_unmanaged_plugin_is_skipped(self):
        target, _ = self.tool.paths('airpods')
        target.mkdir(parents=True)
        setup.setup(self.home, ['airpods'])
        self.assertFalse(any('pkg' in c or c[0] == 'bash' or c[0] == str(ROOT / 'plugins') for c, _ in self.commands))
        self.assertIn('outside this starter', self.output.getvalue())

    def test_owned_build_outputs_survive_and_backend_runs_once(self):
        self.selected = 'airpods'
        target, _ = self.owned('airpods')
        (target / 'build').mkdir()
        (target / 'build/output').write_text('compiled')
        setup.setup(self.home, ['airpods'])
        setup.setup(self.home, ['airpods'])
        self.assertEqual(sum(c == ['bash', 'setup'] for c, _ in self.commands), 1)
        self.assertFalse(any(c[0] == str(ROOT / 'plugins') for c, _ in self.commands))
        self.assertEqual((target / 'build/output').read_text(), 'compiled')

    def test_configured_core_preserves_customizations_and_theme(self):
        journal = self.home / '.local/state/omarchy-mac-starter/journal.json'
        setup.plugins.atomic_json(journal, {'version': 1, 'home': str(self.home),
            'status': 'installed', 'modules': ['shortcuts']})
        setup.setup(self.home, ['activity-monitor'])
        self.assertFalse(any(c[0] == str(ROOT / 'install') or c[:2] == ['omarchy', 'theme'] for c, _ in self.commands))
        self.assertTrue(any(c[0] == str(ROOT / 'plugins') for c, _ in self.commands))
        self.assertFalse(any('--with-shadows' in c for c, _ in self.commands))

    def test_reinstall_runs_backend_after_plugin_removal(self):
        setup.setup(self.home, ['airpods'])
        target, receipt = self.tool.paths('airpods')
        setup.shutil.rmtree(target)
        receipt.unlink()
        setup.setup(self.home, ['airpods'])
        self.assertEqual(sum(c == ['bash', 'setup'] for c, _ in self.commands), 2)

    def test_new_plugin_uses_existing_desktop_shadows(self):
        directory = self.home / '.config/omarchy/ui/panel-shadows'
        directory.mkdir(parents=True)
        for filename in ('KeyboardPanel.qml', 'PanelShadow.qml'):
            (directory / filename).write_text('')
        setup.setup(self.home, ['activity-monitor'])
        self.assertTrue(any('--with-shadows' in c for c, _ in self.commands))

    def test_pending_activation_retries_after_core_finished(self):
        journal = self.home / '.local/state/omarchy-mac-starter/journal.json'
        setup.plugins.atomic_json(journal, {'version': 1, 'home': str(self.home), 'status': 'installed'})
        state_path = journal.with_name('setup.json')
        setup.plugins.atomic_json(state_path, {'backends': {}, 'activation_pending': True, 'previous_theme': 'old'})
        setup.setup(self.home, [])
        self.assertIn((['omarchy', 'theme', 'set', 'mac-starter'], None), self.commands)
        self.assertFalse(json.loads(state_path.read_text())['activation_pending'])

    def test_changed_owned_revision_refused(self):
        self.selected = 'airpods'
        _, receipt = self.owned('airpods')
        state = json.loads(receipt.read_text())
        state['commit'] = 'bad'
        receipt.write_text(json.dumps(state))
        with self.assertRaises(setup.plugins.Refused):
            setup.setup(self.home, ['airpods'])
        self.assertEqual(len(self.commands), 1)

    def test_existing_plugin_without_shadows_keeps_its_variant(self):
        self.selected = 'airpods'
        _, receipt = self.owned('airpods')
        state = json.loads(receipt.read_text())
        state['shadows'] = False
        receipt.write_text(json.dumps(state))
        setup.setup(self.home, ['airpods'])
        self.assertFalse(any(c[0] == str(ROOT / 'plugins') for c, _ in self.commands))
        self.assertFalse(json.loads(receipt.read_text())['shadows'])

    def test_plugin_enable_failure_is_retried_after_source_is_saved(self):
        self.selected = 'airpods'
        def fail_after_source(command, **kwargs):
            result = self.run_command(command, **kwargs)
            if command[:2] == [str(ROOT / 'plugins'), 'install']:
                raise subprocess.CalledProcessError(1, command)
            return result
        self.runner.side_effect = fail_after_source
        with self.assertRaises(subprocess.CalledProcessError):
            setup.setup(self.home, ['airpods'])
        record = self.home / '.local/state/omarchy-mac-starter/setup.json'
        self.assertEqual(json.loads(record.read_text())['plugins_pending'], {'airpods': False})
        self.commands.clear()
        self.runner.side_effect = self.run_command
        setup.setup(self.home, ['airpods'])
        self.assertTrue(any(c[:2] == [str(ROOT / 'plugins'), 'install'] for c, _ in self.commands))
        self.assertEqual(json.loads(record.read_text())['plugins_pending'], {})

    def test_changed_backend_script_refused(self):
        self.selected = 'airpods'
        target, _ = self.owned('airpods')
        (target / 'setup').write_text('changed')
        with self.assertRaises(setup.plugins.Refused):
            setup.setup(self.home, ['airpods'])
        self.assertFalse(any(c[0] == 'bash' for c, _ in self.commands))

    def test_backend_failure_is_retryable(self):
        self.selected = 'airpods'
        self.owned('airpods')
        def failing(command, **kwargs):
            if command == ['bash', 'setup']:
                raise subprocess.CalledProcessError(1, command)
            return self.run_command(command, **kwargs)
        self.runner.side_effect = failing
        with self.assertRaises(subprocess.CalledProcessError):
            setup.setup(self.home, ['airpods'])
        state = json.loads((self.home / '.local/state/omarchy-mac-starter/setup.json').read_text())
        self.assertEqual(state['backends'], {})
        self.runner.side_effect = self.run_command
        setup.setup(self.home, ['airpods'])
        self.assertIn((['bash', 'setup'], self.tool.paths('airpods')[0]), self.commands)

    def test_prior_theme_retained_privately(self):
        previous = self.home / '.local/state/omarchy/current/theme.name'
        previous.parent.mkdir(parents=True)
        previous.write_text('tokyo-night\n')
        setup.setup(self.home, [])
        previous.write_text('mac-starter\n')
        setup.setup(self.home, [])
        record = self.home / '.local/state/omarchy-mac-starter/setup.json'
        self.assertEqual(json.loads(record.read_text())['previous_theme'], 'tokyo-night')
        self.assertEqual(record.stat().st_mode & 0o777, 0o600)

    def test_messages_never_runs_remote_setup(self):
        setup.setup(self.home, ['messages', 'calendar'])
        self.assertFalse(any(c[0] in ('bash', 'hey') for c, _ in self.commands))
        self.assertIn('Calendar is staged', self.output.getvalue())

    def test_airplay_installs_missing_receiver_and_service(self):
        with patch.object(setup.sys.stdin, 'isatty', return_value=True), patch.object(setup.shutil, 'which', return_value=None):
            setup.setup(self.home, ['airplay'])
        self.assertIn((['omarchy', 'pkg', 'aur', 'add', 'doubletake-git'], None), self.commands)
        self.assertIn((['sudo', 'systemctl', 'enable', '--now', 'avahi-daemon'], None), self.commands)

    def test_configuration_errors_fail(self):
        def errors(command, **kwargs):
            self.run_command(command, **kwargs)
            return 'bad binding' if command == ['hyprctl', 'configerrors'] else ''
        self.runner.side_effect = errors
        with self.assertRaisesRegex(setup.plugins.Refused, 'bad binding'):
            setup.setup(self.home, [])

    def test_numbered_selection_and_single_confirmation(self):
        with patch.object(setup.shutil, 'which', return_value=None), patch('builtins.input', side_effect=['1 2', 'n']) as prompt:
            self.assertEqual(setup.main([]), 0)
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(self.commands, [])


if __name__ == '__main__':
    unittest.main()
