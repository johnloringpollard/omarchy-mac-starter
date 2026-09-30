# Mac starter for Omarchy

A starting point for moving from macOS to Omarchy: familiar shortcuts, rounded windows, frosted panels, a transparent top bar, and the day and time on the right. Optional modules add Apple device controls and desktop integrations.

This is an early release extracted from a daily-use Omarchy setup. Its configuration and installer tests run in isolated home directories. Device support still needs testing on your hardware.

![Illustration of the desktop preset](docs/preview.svg)

*Illustration of the preset, not a screenshot of a fresh installation.*

## Start with the desktop

Use an existing **Omarchy 4 installation with Lua-based Hyprland configuration**. The source machine runs Omarchy 4.0.4-1, Hyprland 0.56.2-2, and Quickshell 0.3.1-1. Python 3.11 or newer and Git are required. Other distributions and older `.conf`-based installations are unsupported.

```bash
git clone https://github.com/johnloringpollard/omarchy-mac-starter.git
cd omarchy-mac-starter
./doctor
./install
./install --apply
```

`./install` previews the changes. `--apply` installs the desktop and shortcut modules. It preserves existing custom widgets and reuses your clock, including OmaCal. It never runs a package installer, pairs a device, or signs into an account.

Omarchy watches these configuration files, so applying them can update your live bar and shortcuts immediately. Users who want OmaCal should configure it through the [calendar guide](docs/devices.md#calendar-and-top-right-daytime) before installing the core.

To activate the full light palette, remember your current theme, then select the new one:

```bash
omarchy theme current
omarchy theme set mac-starter
fc-cache
omarchy restart shell
hyprctl reload
hyprctl configerrors
```

The final command should print no errors. Theme selection is a separate step because existing theme hooks can change other settings. If you previously installed the local Apple theme, read [migration notes](docs/migration.md) first.

To install only one core module:

```bash
./install --modules desktop --apply
./install --modules shortcuts --apply
```

These are alternative selections. To change a previously installed selection, uninstall it first. Read the [shortcut guide](docs/shortcuts.md) before applying shortcuts to a customized keyboard setup.

## What is included

| Module | Result |
| --- | --- |
| Desktop | Light theme and original wallpaper, Inter font, 12-pixel rounded windows, soft shadows, compact gaps, transparent top bar, and right-aligned day/time. |
| Frosted panels | White popup surfaces at 75% opacity, compositor blur, and shared shadows for the supplied audio, Bluetooth, display, network, power, weather, agents, and clock widgets. Existing custom widgets stay in place. |
| Shortcuts | Super-based select-all, undo, redo, tabs, and reload, with terminal handling; natural scrolling and three-finger workspace gestures. |
| Magic Mouse | Pinned plugin with local scrolling, selection, edge-contact, USB-C, and battery-query improvements. |
| AirPods | Omapods plus instructions for its matching modified LibrePods daemon. |
| AirPlay | Outgoing desktop mirroring through DoubleTake, including the local fix that removes the two-minute stream timeout. |
| Other plugins | Magic Keyboard/Trackpad, OmaCal, Blip iMessage bridge, and Activity Monitor. |

Menus, tray menus, notifications, and application-specific popups retain their existing components. The source machine's separate notification, podcast, VPN, webcam, Notes, and face-unlock customizations are documented in the [inventory](docs/inventory.md) and [extras guide](docs/extras.md).

## Add a device

List the available modules and prerequisites:

```bash
./plugins list
./plugins install magic-mouse
./plugins install magic-mouse --apply
```

The last command fetches an exact upstream revision, verifies patch checksums, installs the plugin, and enables its widget. **Backend setup is separate.** Follow the [device guide](docs/devices.md) to install the daemon, configure hardware, or sign into a service.

After installing the desktop module, add `--with-shadows` when installing Magic Mouse, AirPods, or Activity Monitor to give their panels the shared shadow styling. Existing plugin directories are preserved; the tool refuses to overwrite them.

`dependencies.lock.json` records the upstream revisions. `patches/` contains the local changes. The repository contains no Bluetooth pairings, device addresses, Apple account sessions, messages, Notes, or saved receiver credentials.

## Restore your settings

If you selected `mac-starter`, first switch to the theme you recorded before installation. For example, if it was Tokyo Night:

```bash
omarchy theme set tokyo-night
./uninstall
./uninstall --apply
fc-cache
omarchy restart shell
hyprctl reload
hyprctl configerrors
```

Uninstall restores only the fields, widget identities, and files recorded by the core installer. Unrelated widgets and later unrelated edits remain. If you changed a field or file that the installer owns, it stops before removing anything and reports the conflict. Keep your edits or resolve the reported conflict before retrying. Its private journal is under `~/.local/state/omarchy-mac-starter/`.

Device backends have separate uninstall steps. Read [device removal](docs/devices.md#remove-a-device-integration) before removing a plugin checkout, especially the AirPods build directory that contains its uninstall manifest.

## Verification and maintenance

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_export.py
```

See [verification](docs/verification.md) for the test scope and hardware checklist, and [architecture](docs/architecture.md) for ownership and update rules. Start an issue with your Omarchy version and device model; omit pairing keys, account tokens, and full private configuration files.

Original starter code is MIT-licensed. Bundled fonts and upstream-derived components keep their own notices. See [credits](THIRD_PARTY.md). This project is independent of Apple and Omarchy.
