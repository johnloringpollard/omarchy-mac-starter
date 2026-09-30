# Verify the starter

## Automated checks

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_export.py
```

The tests use temporary home directories and synthetic Git repositories. They cover preview without writes, repeated installation, interrupted-operation recovery, selective restoration, clock reuse, stock-widget replacement, preservation of later edits, symlink refusal, dependency revision pinning, patch checksum checks, modified checkout refusal, and plugin discovery before enablement.

The `setup` tests replace external commands with recording fakes. They check selection, cancellation, dry-run behavior, package/backend installation order, theme activation, retry behavior, and the boundary between installation and personal configuration. They do not install packages or run backend installers on the test machine.

GitHub Actions runs the same Python checks and parses the authored Lua modules. It does not boot Omarchy or connect Apple hardware.

The initial release was also checked against the installed Omarchy plugin validator. All seven locked upstream revisions were fetched from GitHub, and the functional and shadow patches applied to those exact revisions in temporary directories.

## Stage a complete installation without touching the desktop

Create a temporary home containing the stock configuration:

```bash
test_home=$(mktemp -d)
mkdir -p "$test_home/.config/hypr" "$test_home/.config/omarchy"
cp /usr/share/omarchy/config/hypr/hyprland.lua "$test_home/.config/hypr/"
cp /usr/share/omarchy/config/omarchy/shell.json "$test_home/.config/omarchy/"
./install --home "$test_home" --apply
./doctor --home "$test_home"
./uninstall --home "$test_home" --apply
```

`--home` stages files only. It does not redirect an existing graphical session into that home. Optional `./plugins fetch NAME --home "$test_home"` downloads source there without running upstream setup.

## Test on a desktop

Use a separate Omarchy account or a disposable installation before recommending the starter for another person's primary machine. Configuration tests do not prove rendered appearance or physical device behavior.

1. Record Omarchy, Hyprland, Quickshell, and kernel versions.
2. Apply the preset, select its theme, and check `hyprctl configerrors` after reloading.
3. Open audio, Bluetooth, network, and clock panels. Check corners, transparency, blur, shadows, readability, and outside-click dismissal.
4. Check the day/time at the far right and confirm there is only one clock.
5. Exercise each shortcut in a browser and Ghostty. Confirm undo does not suspend a terminal process.
6. Test natural scrolling and a single workspace step per swipe.
7. Add an unrelated widget, change an unrelated setting, then uninstall and confirm both survive.
8. Test each selected device as described in the device guide. Include reconnect and a fresh login.

Record device model, connection type, package versions, and outcome. The first release does not claim fresh-machine visual testing, AirPlay receiver coverage, or successful physical pairing on other computers.
