# Migrate an existing customized desktop

The installer targets an existing Omarchy installation. It preserves custom widgets and refuses to replace unmanaged files at its destinations.

If you already use the original local `apple` theme with an `apple-desktop` hook, keep that setup while you evaluate this starter. Its hook can restore an old whole-bar snapshot when changing themes. The starter detects an active legacy hook and refuses the desktop install.

To migrate that setup:

1. Back up `~/.config/hypr/`, `~/.config/omarchy/`, and `~/.local/state/omarchy/apple/` to a private local directory.
2. Inspect the old `apple-desktop` hook and its `active.json` restoration record. Compare the saved bar layout with the current one.
3. Disable the legacy hook by moving it outside `theme-set.d`. Retain its backup records.
4. Resolve existing files at starter destinations explicitly. Keep a customized file or move it into your private backup before installing its replacement.
5. Run `./install` and inspect the preview. Apply it only after the remaining changes match your intended setup.
6. Select the new theme, reload, and check the bar and shortcuts.

The repository does not automate this migration because existing installations contain independent customizations made after the old snapshot. Do not restore that snapshot over your current bar merely to make installation succeed.

For pre-existing third-party plugins, save your changes and complete any backend cleanup before moving the old checkout. The plugin installer does not adopt or overwrite an unmanaged directory.
