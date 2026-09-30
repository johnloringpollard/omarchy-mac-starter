import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('starter', ROOT / 'scripts/starter.py')
starter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(starter)


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.write(starter.HYPR, '-- personal config\n')
        self.original = {'bar': {'position': 'bottom', 'transparent': False,
            'layout': {'left': [{'id': 'omarchy.menu'}],
                       'center': [{'id': 'custom.clock', 'format': 'HH:mm', 'custom': 42}, {'id': 'custom.weather'}],
                       'right': [{'id': 'custom.audio', 'volume': 10}]}}}
        self.save(self.original)
        self.write(starter.TOML, '# preserved\n[font]\nbase-size = 11\n[popups]\nbackground-alpha = 0.9\n')

    def write(self, name, value):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)

    def save(self, value):
        self.write(starter.SHELL, json.dumps(value))

    def shell(self):
        return json.loads((self.home / starter.SHELL).read_text())

    def cli(self, command, *args, success=True):
        result = subprocess.run([str(ROOT / command), '--home', str(self.home), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return result

    def test_preview_makes_no_files(self):
        before = {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.cli('install')
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_install_repeat_uninstall_preserves_unrelated_changes(self):
        self.cli('install', '--apply')
        self.cli('install', '--apply')
        self.cli('doctor')
        shell = self.shell()
        self.assertEqual(shell['bar']['layout']['right'][-1]['id'], 'custom.clock')
        self.assertEqual(shell['bar']['layout']['right'][-1]['custom'], 42)
        shell['idle'] = {'lock': 1234}
        shell['bar']['layout']['right'].insert(0, {'id': 'new.widget', 'settings': True})
        self.save(shell)
        with (self.home / starter.HYPR).open('a') as file:
            file.write('-- added later\n')
        with (self.home / starter.TOML).open('a') as file:
            file.write('border-width = 7\n')
        self.cli('uninstall', '--apply')
        restored = self.shell()
        self.assertEqual(restored['idle']['lock'], 1234)
        self.assertEqual(restored['bar']['layout']['center'], self.original['bar']['layout']['center'])
        self.assertEqual(restored['bar']['layout']['right'][0]['id'], 'new.widget')
        self.assertIn('-- added later', (self.home / starter.HYPR).read_text())
        self.assertIn('border-width = 7', (self.home / starter.TOML).read_text())
        self.assertNotIn('BEGIN mac-starter', (self.home / starter.HYPR).read_text())
        self.cli('uninstall', '--apply')

    def test_owned_field_conflict_preserves_all_files(self):
        self.cli('install', '--apply')
        shell = self.shell()
        shell['bar']['transparent'] = 'user-change'
        self.save(shell)
        self.cli('uninstall', '--apply', success=False)
        self.assertEqual(self.shell()['bar']['transparent'], 'user-change')
        self.assertTrue((self.home / '.config/hypr/mac-starter/desktop.lua').exists())
        self.cli('doctor', success=False)

    def test_unrelated_clock_settings_survive(self):
        self.cli('install', '--apply')
        shell = self.shell()
        shell['bar']['layout']['right'][-1]['custom'] = 99
        self.save(shell)
        self.cli('uninstall', '--apply')
        self.assertEqual(self.shell()['bar']['layout']['center'][0]['custom'], 99)

    def test_omacal_is_reused(self):
        self.original['bar']['layout']['center'][0]['id'] = 'crmne.omacal'
        self.save(self.original)
        self.cli('install', '--apply')
        clocks = [w for widgets in self.shell()['bar']['layout'].values() for w in widgets if 'clock' in w['id'] or 'omacal' in w['id']]
        self.assertEqual(len(clocks), 1)
        self.assertEqual(clocks[0]['id'], 'crmne.omacal')

    def test_clock_clone_with_arbitrary_id_is_reused(self):
        self.original['bar']['layout']['center'][0]['id'] = 'custom.time'
        self.save(self.original)
        self.write('.config/omarchy/plugins/custom.time/manifest.json',
                   json.dumps({'omarchy': {'clonedFrom': 'omarchy.clock'}}))
        self.cli('install', '--apply')
        self.assertEqual(self.shell()['bar']['layout']['right'][-1]['id'], 'custom.time')

    def test_added_clock_changed_by_user_is_preserved(self):
        self.original['bar']['layout']['center'].pop(0)
        self.save(self.original)
        self.cli('install', '--apply')
        shell = self.shell()
        shell['bar']['layout']['right'][-1]['custom'] = True
        self.save(shell)
        self.cli('uninstall', '--apply', success=False)
        self.assertTrue(self.shell()['bar']['layout']['right'][-1]['custom'])

    def test_symlink_outside_home_is_rejected(self):
        path = self.home / '.config/hypr/mac-starter'
        with tempfile.TemporaryDirectory() as other:
            path.symlink_to(other, target_is_directory=True)
            self.cli('install', '--apply', success=False)
            self.assertEqual(list(Path(other).iterdir()), [])

    def test_partial_install_and_partial_uninstall_recover(self):
        operations = starter.plan(starter.Files(self.home), ['desktop', 'shortcuts'])
        journal = {'version': 1, 'home': str(self.home), 'modules': ['desktop', 'shortcuts'], 'status': 'installing', 'operations': operations}
        self.write(starter.STATE + '/journal.json', json.dumps(journal))
        fs = starter.Files(self.home, apply=True)
        for operation in operations[:7]:
            starter.operate(fs, operation, operation['after'], True)
        self.cli('install', '--apply')
        journal['status'] = 'removing'
        self.write(starter.STATE + '/journal.json', json.dumps(journal))
        fs = starter.Files(self.home, apply=True)
        for operation in list(reversed(operations))[:4]:
            starter.operate(fs, operation, operation['before'], True)
        self.cli('uninstall', '--apply')
        self.assertEqual(self.shell()['bar']['layout'], self.original['bar']['layout'])

    def test_shortcuts_only_does_not_change_shell(self):
        before = (self.home / starter.SHELL).read_bytes()
        self.cli('install', '--apply', '--modules', 'shortcuts')
        self.assertEqual(before, (self.home / starter.SHELL).read_bytes())

    def test_existing_unmanaged_file_is_not_overwritten(self):
        self.write('.config/hypr/mac-starter/desktop.lua', '-- user file')
        self.cli('install', '--apply', success=False)
        self.assertEqual((self.home / '.config/hypr/mac-starter/desktop.lua').read_text(), '-- user file')

    def test_stock_panels_are_replaced_and_user_widget_settings_restored(self):
        self.original['bar']['layout']['center'][0]['id'] = 'omarchy.clock'
        self.original['bar']['layout']['right'][0]['id'] = 'omarchy.audio'
        self.save(self.original)
        self.cli('install', '--apply')
        self.cli('install', '--apply')
        self.cli('doctor')
        shell = self.shell()
        audio = next(w for w in shell['bar']['layout']['right'] if w['id'] == 'macstarter.audio')
        audio['volume'] = 30
        self.save(shell)
        self.assertEqual(shell['bar']['layout']['right'][-1]['id'], 'macstarter.clock')
        self.assertTrue((self.home / '.config/omarchy/ui/panel-shadows/PanelShadow.qml').exists())
        self.cli('uninstall', '--apply')
        self.assertEqual(self.shell()['bar']['layout']['right'][0], {'id': 'omarchy.audio', 'volume': 30})
        self.assertEqual(self.shell()['bar']['layout']['center'], self.original['bar']['layout']['center'])

    def test_legacy_restore_hook_blocks_install_before_writes(self):
        self.write('.config/omarchy/hooks/theme-set.d/apple-desktop', 'legacy hook')
        self.write('.local/state/omarchy/apple/active.json', '{}')
        self.cli('install', '--apply', success=False)
        self.assertFalse((self.home / '.config/hypr/mac-starter/desktop.lua').exists())

    def test_shadow_dependents_block_shared_component_removal(self):
        self.cli('install', '--apply')
        self.write(starter.STATE + '/plugins/airpods.json', '{"shadows":true}')
        self.cli('uninstall', '--apply', success=False)
        self.assertTrue((self.home / '.config/omarchy/ui/panel-shadows/PanelShadow.qml').exists())


if __name__ == '__main__':
    unittest.main()
