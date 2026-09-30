import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('plugins', Path(__file__).resolve().parents[1] / 'scripts/plugins.py')
plugins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plugins)


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.home = base / 'home'
        self.root = base / 'starter'
        self.source = base / 'source'
        self.source.mkdir()
        self.root.mkdir()
        (self.root / 'patches').mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.source), *args], text=True).strip()
        git('init', '-q')
        git('config', 'user.name', 'Test')
        git('config', 'user.email', 'test@example.invalid')
        (self.source / 'manifest.json').write_text('{"id":"test.widget","version":"1.0.0"}\n')
        (self.source / 'value.txt').write_text('original\n')
        git('add', '.')
        git('commit', '-qm', 'original')
        self.commit = git('rev-parse', 'HEAD')
        (self.source / 'value.txt').write_text('newer upstream\n')
        git('commit', '-qam', 'newer')
        data = b'--- a/value.txt\n+++ b/value.txt\n@@ -1 +1 @@\n-original\n+patched\n'
        (self.root / 'patches/fix.patch').write_bytes(data)
        self.document = {'schema': 1, 'modules': {'sample': {
            'id': 'test.widget', 'url': 'https://github.com/example/test',
            'commit': self.commit, 'version': '1.0.0', 'packages': [], 'setup': [],
            'patches': [{'path': 'patches/fix.patch', 'kind': 'functional', 'sha256': plugins.digest(data)}]}}}
        self.write_lock()
        original_run = plugins.run
        def local_run(args, cwd=None):
            if args[:2] == ['git', 'clone']:
                args = [str(self.source) if x == 'https://github.com/example/test' else x for x in args]
            if args[0] == 'omarchy':
                raise AssertionError('Test home must never invoke live shell')
            return original_run(args, cwd)
        self.mock_run = patch.object(plugins, 'run', side_effect=local_run)
        self.mock_run.start()
        self.addCleanup(self.mock_run.stop)
        self.tool = plugins.Plugins(self.home, self.root, sandbox=True)

    def write_lock(self):
        (self.root / 'dependencies.lock.json').write_text(json.dumps(self.document))

    def test_preview_does_not_create_home(self):
        self.tool.install('sample')
        self.assertFalse(self.home.exists())

    def test_fetch_pins_old_revision_and_applies_patch_once(self):
        cache = self.tool.fetch('sample')
        self.assertEqual((cache / 'value.txt').read_text(), 'patched\n')
        self.assertEqual(plugins.run(['git', '-C', str(cache), 'rev-parse', 'HEAD']), self.commit)
        self.assertEqual(self.tool.fetch('sample'), cache)

    def test_changed_cache_refused(self):
        cache = self.tool.fetch('sample')
        (cache / 'value.txt').write_text('user edit')
        with self.assertRaises(plugins.Refused):
            self.tool.fetch('sample')

    def test_install_repeat_remove_and_repeat_remove(self):
        self.tool.install('sample', apply=True)
        target, receipt = self.tool.paths('sample')
        first = receipt.read_bytes()
        self.tool.install('sample', apply=True)
        self.assertEqual(first, receipt.read_bytes())
        self.assertEqual((target / 'value.txt').read_text(), 'patched\n')
        self.tool.remove('sample', apply=True)
        self.assertFalse(target.exists())
        self.assertFalse(receipt.exists())
        self.tool.remove('sample', apply=True)

    def test_user_edits_and_build_outputs_preserved(self):
        self.tool.install('sample', apply=True)
        target, receipt = self.tool.paths('sample')
        (target / 'build').mkdir()
        (target / 'build/install_manifest.txt').write_text('important uninstall manifest')
        with self.assertRaises(plugins.Refused):
            self.tool.remove('sample', apply=True)
        self.assertTrue(receipt.exists())
        self.assertTrue((target / 'build/install_manifest.txt').exists())

    def test_unmanaged_plugin_refused(self):
        target, _ = self.tool.paths('sample')
        target.mkdir(parents=True)
        (target / 'mine').write_text('keep')
        with self.assertRaises(plugins.Refused):
            self.tool.install('sample', apply=True)
        self.assertEqual((target / 'mine').read_text(), 'keep')

    def test_checksum_mismatch_refused(self):
        (self.root / 'patches/fix.patch').write_text('changed')
        with self.assertRaises(plugins.Refused):
            plugins.Plugins(self.home, self.root, sandbox=True)

    def test_managed_path_symlink_refused(self):
        self.home.mkdir()
        outside = self.home.parent / 'outside'
        outside.mkdir()
        (self.home / '.config').symlink_to(outside)
        with self.assertRaises(plugins.Refused):
            self.tool.install('sample', apply=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_shadow_dependency_required(self):
        self.tool.modules['sample']['patches'][0]['kind'] = 'shadows'
        with self.assertRaises(plugins.Refused):
            self.tool.install('sample', apply=True, shadows=True)

    def test_shadow_flag_without_shadow_patch_records_no_dependency(self):
        self.tool.install('sample', apply=True, shadows=True)
        _, receipt = self.tool.paths('sample')
        self.assertFalse(json.loads(receipt.read_text())['shadows'])

    def test_git_head_change_refused(self):
        cache = self.tool.fetch('sample')
        plugins.run(['git', '-C', str(cache), 'checkout', '--force', 'origin/HEAD'])
        with self.assertRaises(plugins.Refused):
            self.tool.fetch('sample')

    def test_local_branch_preserved(self):
        self.tool.install('sample', apply=True)
        target, _ = self.tool.paths('sample')
        plugins.run(['git', '-C', str(target), 'branch', 'keep-my-work'])
        with self.assertRaises(plugins.Refused):
            self.tool.remove('sample', apply=True)
        self.assertTrue(target.exists())

    def test_discovery_waits_before_enable(self):
        self.tool.fetch('sample')
        self.tool.sandbox = False
        calls = []
        responses = iter(['[]', '[{"id":"test.widget"}]'])
        delegate = plugins.run
        def commands(args, cwd=None):
            if args[0] in ('omarchy', 'omarchy-shell'):
                calls.append(args)
                if args[1:3] == ['plugin', 'list']:
                    return next(responses)
                return ''
            return delegate(args, cwd)
        with patch.object(plugins, 'run', side_effect=commands), patch.object(plugins.shutil, 'which', return_value='/usr/bin/omarchy'), patch.object(plugins.time, 'sleep'):
            self.tool.install('sample', apply=True)
        self.assertEqual(calls[-1], ['omarchy', 'plugin', 'enable', 'test.widget'])
        self.assertEqual(sum(c[1:3] == ['plugin', 'list'] for c in calls), 2)
        self.assertIn(['omarchy-shell', 'shell', 'rescanPlugins'], calls)

    def test_removal_keeps_latest_widget_settings_backup(self):
        self.tool.install('sample', apply=True)
        shell = self.home / '.config/omarchy/shell.json'
        shell.write_text(json.dumps({'bar': {'layout': {'right': [{'id': 'test.widget', 'custom': 42}]}}}))
        self.tool.sandbox = False
        delegate = plugins.run
        def commands(args, cwd=None):
            if args[0] == 'omarchy':
                return ''
            return delegate(args, cwd)
        with patch.object(plugins, 'run', side_effect=commands):
            self.tool.remove('sample', apply=True)
        backups = list((self.home / '.local/state/omarchy-mac-starter/plugins').glob('*widget-backup*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text())['widgets'][0]['custom'], 42)


if __name__ == '__main__':
    unittest.main()
