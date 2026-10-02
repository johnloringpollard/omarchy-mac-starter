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

## Upgrade an existing starter installation

The starter's installation journal preserves the version it installed. Pulling new source and rerunning setup does not replace that journal or upgrade its owned files.

1. Keep a private backup of your configuration and installation journal.
2. Run `./plugins list` and note the starter-managed optional plugins. Remove plugins that depend on shared shadows using the documented removal procedure. Preserve their personal configuration and review backend cleanup separately.
3. Choose a theme other than `mac-starter` or `mac-starter-dark`, then run `./uninstall --apply`. Resolve reported conflicts by preserving your edits before proceeding.
4. Run `git pull --ff-only`, then `./setup` and select the optional plugins you want.
5. Open **Mac Starter Appearance** and select your appearance preference.

The new installation includes both themes, its own appearance chooser and timer. It does not overwrite the standalone Mac Style package's configuration or timer.
