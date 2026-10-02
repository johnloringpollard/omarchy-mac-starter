from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


def rgb(value):
    return [int(value[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def luminance(values):
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    low, high = sorted((luminance(a), luminance(b)))
    return (high + .05) / (low + .05)


class ThemeTests(unittest.TestCase):
    def test_dark_text_remains_readable_over_a_white_window(self):
        path = ROOT / 'assets/theme-dark'
        palette = tomllib.loads((path / 'colors.toml').read_text())
        shell = tomllib.loads((path / 'shell.toml').read_text())
        for area in ('bar', 'popups', 'tooltip', 'notifications', 'launcher', 'menu', 'polkit', 'lock'):
            with self.subTest(area=area):
                surface = shell[area]
                alpha = surface['background-alpha']
                backdrop = [v * alpha + (1 - alpha) for v in rgb(surface['background'])]
                self.assertGreaterEqual(contrast(rgb(surface['text']), backdrop), 7)
                self.assertGreaterEqual(contrast(rgb(palette['muted']), backdrop), 4.5)

    def test_selected_menu_labels_have_contrast(self):
        for theme in ('theme', 'theme-dark'):
            shell = tomllib.loads((ROOT / 'assets' / theme / 'shell.toml').read_text())
            for area in ('launcher', 'menu'):
                with self.subTest(theme=theme, area=area):
                    surface = shell[area]
                    self.assertGreaterEqual(contrast(rgb(surface['selected-text']), rgb(surface['selected-background'])), 4.5)

    def test_light_and_dark_keep_geometry_and_terminal_palette(self):
        light = ROOT / 'assets/theme'
        dark = ROOT / 'assets/theme-dark'
        for name in ('alacritty.toml', 'ghostty.conf', 'foot.ini', 'kitty.conf'):
            self.assertEqual((light / name).read_bytes(), (dark / name).read_bytes())
        a = tomllib.loads((light / 'shell.toml').read_text())
        b = tomllib.loads((dark / 'shell.toml').read_text())
        self.assertEqual(a['font'], b['font'])
        self.assertEqual(a['spacing'], b['spacing'])
        self.assertEqual(a['bar']['size-horizontal'], b['bar']['size-horizontal'])


if __name__ == '__main__':
    unittest.main()
