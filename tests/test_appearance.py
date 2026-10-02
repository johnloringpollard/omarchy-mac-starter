import importlib.machinery
import importlib.util
import os
import multiprocessing
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('mac_style', str(Path(__file__).resolve().parents[1] / 'assets/appearance/mac-starter-appearance'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
loader.exec_module(module)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.old_tz = os.environ.get('TZ')
        self.timezone('America/New_York')
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.theme = self.root / 'theme.name'
        self.theme.write_text('mac-starter')
        self.applied = []
        self.scheduler = module.Scheduler(self.root / 'config', self.root / 'state', self.theme, self.apply)

    def tearDown(self):
        if self.old_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = self.old_tz
        time.tzset()
        self.directory.cleanup()

    def timezone(self, name):
        os.environ['TZ'] = name
        time.tzset()

    def apply(self, theme):
        self.applied.append(theme)
        self.theme.write_text(theme)

    def at(self, value):
        return datetime.fromisoformat(value).astimezone()

    def run_at(self, command, value, times=()):
        return self.scheduler.run(command, times, self.at(value))

    def test_apply_activates_saved_mode_from_an_unrelated_theme(self):
        for mode in ('auto', 'light', 'dark'):
            module.atomic_json(self.scheduler.config_file, module.DEFAULT_CONFIG | {'mode': mode})
            self.theme.write_text('tokyo-night')
            result = self.run_at('apply', '2026-01-02T20:00')
            self.assertEqual(result['preference'], mode)
            self.assertEqual(result['current_theme'], module.THEMES['dark' if mode == 'auto' else mode])

    def test_enable_applies_schedule_on_first_install(self):
        result = self.run_at('enable', '2026-01-02T20:00')
        self.assertEqual(result['mode'], 'auto')
        self.assertEqual(self.applied, ['mac-starter-dark'])
        self.assertTrue(module.read_json(self.scheduler.config_file, {})['enabled'])

    def test_enable_preserves_other_theme_and_fixed_mode(self):
        self.theme.write_text('tokyo-night')
        self.assertEqual(self.run_at('enable', '2026-01-02T20:00')['mode'], 'paused-other-theme')
        self.assertEqual(self.applied, [])
        self.run_at('dark', '2026-01-03T12:00')
        self.assertEqual(self.run_at('enable', '2026-01-03T12:01')['mode'], 'dark')
        self.assertEqual(self.applied, ['mac-starter-dark'])

    def test_default_day_and_cross_midnight(self):
        for value, expected in [('2026-01-02T06:59', 'dark'), ('2026-01-02T07:00', 'light'), ('2026-01-02T19:00', 'dark'), ('2026-01-03T00:01', 'dark')]:
            with self.subTest(value=value):
                self.assertEqual(module.schedule_interval(module.DEFAULT_CONFIG, self.at(value)).kind, expected)

    def test_overnight_light_schedule(self):
        config = module.validate_config({'light': '19:00', 'dark': '07:00'})
        self.assertEqual(module.schedule_interval(config, self.at('2026-01-02T23:00')).kind, 'light')
        self.assertEqual(module.schedule_interval(config, self.at('2026-01-02T12:00')).kind, 'dark')

    def test_spring_transition_uses_next_days_offset(self):
        result = module.schedule_interval(module.DEFAULT_CONFIG, self.at('2026-03-07T20:00'))
        self.assertEqual(result.next_time.isoformat(), '2026-03-08T07:00:00-04:00')

    def test_fall_transition_uses_next_days_offset(self):
        result = module.schedule_interval(module.DEFAULT_CONFIG, self.at('2026-10-31T20:00'))
        self.assertEqual(result.next_time.isoformat(), '2026-11-01T07:00:00-05:00')

    def test_nonexistent_spring_time_moves_forward(self):
        config = module.validate_config({'light': '02:30'})
        result = module.schedule_interval(config, self.at('2026-03-08T01:00'))
        self.assertEqual(result.next_time.isoformat(), '2026-03-08T03:30:00-04:00')

    def test_spring_gap_colliding_times_keep_wall_clock_order(self):
        config = module.validate_config({'light': '02:30', 'dark': '03:30'})
        result = module.schedule_interval(config, self.at('2026-03-08T03:40'))
        self.assertEqual(result.kind, 'dark')

    def test_concurrent_commands_only_apply_once(self):
        log = self.root / 'applications'
        def apply(theme):
            with log.open('a') as output:
                output.write(theme + '\n')
            time.sleep(0.05)
            self.theme.write_text(theme)
        self.scheduler.apply = apply
        context = multiprocessing.get_context('fork')
        processes = [context.Process(target=self.run_at, args=('dark', '2026-01-02T12:00')) for _ in range(3)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(log.read_text(), 'mac-starter-dark\n')

    def test_fall_fold_does_not_repeat_boundary(self):
        config = module.validate_config({'light': '01:30'})
        first = module.schedule_interval(config, self.at('2026-11-01T01:40:00-04:00'))
        repeated_hour = module.schedule_interval(config, self.at('2026-11-01T01:10:00-05:00'))
        self.assertEqual(first.anchor, repeated_hour.anchor)
        self.assertEqual(repeated_hour.kind, 'light')

    def test_auto_and_repeated_checks_are_idempotent(self):
        self.run_at('auto', '2026-01-02T12:00')
        self.run_at('check', '2026-01-02T12:01')
        self.assertEqual(self.applied, [])
        self.run_at('check', '2026-01-02T19:00')
        self.run_at('check', '2026-01-02T19:01')
        self.assertEqual(self.applied, ['mac-starter-dark'])

    def test_fixed_modes_persist_across_boundaries_and_restart(self):
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                self.run_at(mode, '2026-01-02T12:00')
                reloaded = module.Scheduler(self.root / 'config', self.root / 'state', self.theme, self.apply)
                for value in ('2026-01-02T19:01', '2026-01-03T07:01'):
                    result = reloaded.run('check', now=self.at(value))
                    self.assertEqual(result['mode'], mode)
                    self.assertEqual(result['current_theme'], module.THEMES[mode])
                    self.assertIsNone(result['next_transition'])
                self.run_at('schedule', '2026-01-03T12:00', ('08:00', '20:00'))
                self.assertEqual(self.run_at('status', '2026-01-03T12:00')['preference'], mode)

    def test_legacy_config_keeps_automatic_and_existing_hold(self):
        module.atomic_json(self.scheduler.config_file, {'enabled': True, 'light': '07:00', 'dark': '19:00'})
        self.theme.write_text('mac-starter-dark')
        interval = module.schedule_interval(module.DEFAULT_CONFIG, self.at('2026-01-02T12:00'))
        module.atomic_json(self.scheduler.state_file, {'last_theme': 'mac-starter-dark', 'hold_interval': interval.anchor})
        self.assertEqual(self.run_at('check', '2026-01-02T12:01')['mode'], 'hold')
        self.assertEqual(self.run_at('check', '2026-01-03T07:01')['current_theme'], 'mac-starter')

    def test_menu_selection_and_cancel(self):
        for label, preference in [('Always light', 'light'), ('Always dark', 'dark'), ('Automatic', 'auto')]:
            with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, label + '\n')):
                result = module.choose_mode(self.scheduler)
                self.assertEqual(result['preference'], preference)
        before = self.scheduler.config_file.read_bytes()
        for code, output in [(1, ''), (0, '')]:
            with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, output)):
                self.assertIsNone(module.choose_mode(self.scheduler))
        self.assertEqual(self.scheduler.config_file.read_bytes(), before)

    def test_menu_automatic_enables_timer_and_failure_preserves_preference(self):
        self.run_at('dark', '2026-01-02T12:00')
        before = self.scheduler.config_file.read_bytes()
        error = subprocess.CalledProcessError(1, ['systemctl'])
        with patch.object(module.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, 'Automatic\n'), error]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                module.choose_mode(self.scheduler)
            self.assertEqual(run.call_args.args[0], ['systemctl', '--user', 'enable', '--now', 'mac-starter-appearance.timer'])
        self.assertEqual(self.scheduler.config_file.read_bytes(), before)

    def test_picker_change_holds_until_next_transition(self):
        self.run_at('auto', '2026-01-02T12:00')
        self.theme.write_text('mac-starter-dark')
        self.assertEqual(self.run_at('check', '2026-01-02T12:01')['mode'], 'hold')
        self.run_at('check', '2026-01-02T12:02')
        self.assertEqual(self.applied, [])
        self.run_at('check', '2026-01-03T07:00')
        self.assertEqual(self.applied, ['mac-starter'])

    def test_auto_clears_manual_hold(self):
        self.run_at('dark', '2026-01-02T12:00')
        self.assertEqual(self.run_at('auto', '2026-01-02T12:01')['mode'], 'auto')
        self.assertEqual(self.applied, ['mac-starter-dark', 'mac-starter'])

    def test_other_theme_is_untouched_and_return_is_manual(self):
        self.run_at('auto', '2026-01-02T12:00')
        self.theme.write_text('tokyo-night')
        self.assertEqual(self.run_at('check', '2026-01-02T20:00')['mode'], 'paused-other-theme')
        self.assertEqual(self.applied, [])
        self.theme.write_text('mac-starter')
        self.assertEqual(self.run_at('check', '2026-01-02T20:01')['mode'], 'hold')
        self.assertEqual(self.applied, [])

    def test_failed_apply_does_not_save_success(self):
        self.run_at('auto', '2026-01-02T12:00')
        before = self.scheduler.state_file.read_bytes()
        with patch.object(self.scheduler, 'apply', side_effect=subprocess.CalledProcessError(1, ['omarchy'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_at('dark', '2026-01-02T12:01')
        self.assertEqual(self.scheduler.state_file.read_bytes(), before)
        self.assertEqual(self.theme.read_text(), 'mac-starter')

    def test_timezone_jump_follows_new_local_schedule(self):
        instant = self.at('2026-01-02T18:00:00-05:00')
        self.scheduler.run('auto', now=instant)
        self.timezone('Europe/London')
        result = self.scheduler.run('check', now=instant)
        self.assertEqual(result['current_theme'], 'mac-starter-dark')
        self.assertEqual(result['next_transition'], '2026-01-03T07:00:00+00:00')

    def test_config_validation_and_schedule(self):
        for config in [{'light': '24:00'}, {'light': '7:00'}, {'dark': '07:00'}, {'enabled': 'true'}, {'mode': 'invalid'}, []]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                module.validate_config(config)
        result = self.run_at('schedule', '2026-01-02T12:00', ('08:00', '20:00'))
        self.assertEqual(result['schedule'], {'light': '08:00', 'dark': '20:00'})
        self.assertEqual(result['mode'], 'disabled')
        self.scheduler.config_file.write_text('{"light":"broken"}')
        with self.assertRaises(ValueError):
            self.run_at('check', '2026-01-02T12:01')

    def test_xdg_paths_and_omarchy_fixed_path(self):
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root / 'xdg-config'), 'XDG_STATE_HOME': str(self.root / 'xdg-state')}):
            scheduler = module.Scheduler()
        self.assertEqual(scheduler.config_file, self.root / 'xdg-config/mac-starter-appearance/config.json')
        self.assertEqual(scheduler.state_file, self.root / 'xdg-state/mac-starter-appearance/state.json')
        self.assertEqual(scheduler.theme_file, Path.home() / '.local/state/omarchy/current/theme.name')

    def test_apply_uses_exact_argv(self):
        with patch.object(module.subprocess, 'run') as run:
            module.Scheduler.apply_theme('mac-starter-dark')
        run.assert_called_once_with(['omarchy', 'theme', 'set', 'mac-starter-dark'], check=True)


if __name__ == '__main__':
    unittest.main()
