# Set up optional devices and services

Run commands from the starter checkout unless a step changes directory. A plugin source install does not install its backend or connect to your devices. Run setup from an interactive terminal so upstream installers can request administrator access when needed.

`./plugins install NAME` previews installation. Add `--apply` to fetch the pinned revision and enable its widget. Add `--with-shadows` at initial installation to apply available panel-shadow patches after installing the core desktop module. To change the shadow selection later, remove the managed checkout first.

## Magic Mouse

```bash
./plugins install magic-mouse --apply --with-shadows
cd ~/.config/omarchy/plugins/io.github.maikunari.magic-mouse
bash install.sh
```

The upstream installer installs the Python daemon and its service, grants device access through udev, and configures the kernel mouse driver. It can install `python-evdev` and request sudo access. Read its output and complete any reconnect or login instructions.

The functional patch includes USB-C identifiers, asynchronous battery queries, edge-contact rejection, vertical scrolling during selection, click/drag gesture suppression, and improved short scroll strokes. The optional shadow patch changes only the panel presentation. A current Omarchy hover API compatibility change is part of the functional patch.

`modules/magic-mouse/config.toml` is a portable tuning preset. Back up your existing `~/.config/magic-mouse/config.toml` before copying it there. The starter does not overwrite mouse tuning automatically. Adjust tracking and scroll speed for your display and hand movement.

Check the service and pair the mouse through Bluetooth settings:

```bash
systemctl --user status magic-mouse.service
```

Verify small scroll movements, momentum, horizontal scrolling, text selection while scrolling, two-finger workspace swipes, and battery readings. A running service alone does not prove these interactions work.

## AirPods

```bash
./plugins install airpods --apply --with-shadows
cd ~/.config/omarchy/plugins/io.github.thisisgm.omapods
bash setup
```

This builds the plugin's modified LibrePods daemon and installs it under `~/.local`. It requires CMake, Ninja, Qt6 connectivity/tools/declarative, pkgconf, libpulse, and OpenSSL. The setup script installs its listed missing packages and enables `librepods.service`. If CMake reports missing OpenSSL, install the Arch `openssl` package.

Pair your AirPods through Bluetooth settings, then check:

```bash
systemctl --user status librepods.service
```

The widget can hide while disconnected. Test pod/case battery readings and the listening modes supported by your model. Do not replace this daemon with an arbitrary LibrePods build: the widget expects this fork's status file and control interface.

The source machine's automatic output-switching script contains a specific Bluetooth address. It is intentionally excluded. Choose an audio output through the normal audio panel.

## AirPlay mirroring

```bash
./plugins install airplay --apply
omarchy pkg add avahi jq gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav pipewire xdg-desktop-portal-hyprland
omarchy pkg aur add doubletake-git
sudo systemctl enable --now avahi-daemon
```

The source setup has `doubletake-git 0.4.0.r35.gae06722-1`. Arch/AUR package versions follow your configured repositories; the plugin commit is pinned separately. Review the AUR build instructions when your package helper presents them.

Open the AirPlay widget, select a receiver on your local network, and enter its displayed PIN if requested. The Wayland portal asks which screen or window to share. Audio behavior depends on the plugin's audio setting and backend support.

This sends the Linux desktop to an Apple TV or compatible receiver. It does not receive an iPhone screen. Test a session longer than two minutes to verify the included timeout fix. Use the plugin's receiver-specific firewall controls only if your firewall blocks streaming; do not open broad port ranges to untrusted networks.

## Magic Keyboard and Magic Trackpad

```bash
./plugins install magic-devices --apply
```

Use the OMagic panel to connect devices and apply trackpad preferences. Its optional Fn-mode helper is a separate administrator installation described in the plugin README. The helper was not installed on the source machine, so this starter does not claim it was physically verified. OMagic does not provide Touch ID authentication.

## Calendar and top-right day/time

OmaCal source installation deliberately stops before enabling its widget, to avoid creating a second clock:

```bash
./plugins install calendar --apply
```

For a fresh Omarchy setup, configure OmaCal **before** installing the core desktop module:

```bash
omarchy plugin disable omarchy.clock
omarchy plugin enable crmne.omacal
omarchy bar move crmne.omacal --section right
```

If your clock already has a custom ID, disable that clock instead of `omarchy.clock`. If the core starter is already installed, restore its configuration with `./uninstall --apply` first, replace the clock, then reinstall the core. The installer will recognize OmaCal, preserve its settings, and apply `dddd h:mm AP` at the right edge.

To connect HEY, install `hey-cli` and `jq`, then run `hey setup` interactively. Account authentication stays on your machine. Without an account backend, do not assume the calendar contains your events.

## iMessage and contacts

```bash
./plugins install messages --apply
omarchy pkg add openssh bun jq libnotify wl-clipboard xdg-utils
cd ~/.config/omarchy/plugins/nixfred.blip
bash scripts/blip-setup
```

Blip requires a reachable Mac signed into Messages. Setup asks for the Mac's SSH destination, changes local SSH configuration, installs command-line shims, and installs bridge tools on the Mac. Follow its Full Disk Access and Automation permission instructions on macOS.

This setup is optional and contacts a second machine. Inspect the upstream setup script before running it. No hostnames, SSH keys, allowlists, or message history are supplied by this repository.

## Activity Monitor

```bash
./plugins install activity-monitor --apply --with-shadows
```

The panel shows CPU, memory, storage, and process information. Its optional privileged power-reading helper is not installed by this starter.

## Remove a device integration

Complete backend cleanup **before** deleting its source checkout. `./plugins remove NAME --apply` removes only an unchanged starter-managed checkout and disables its widget. It preserves packages, device rules, services, pairing information, and account data. Its removal record saves the latest widget settings locally when the live shell is used.

| Module | Cleanup before source removal |
| --- | --- |
| Magic Mouse | Run `bash uninstall.sh` from the plugin checkout. Inspect the upstream script and its output; it preserves tuning and some input configuration. |
| AirPods | Disable/stop `librepods.service`. Inspect `daemon/build/install_manifest.txt` and remove only the installed files it lists. Keep the manifest until cleanup is complete. Preserve pairing data unless you intend to pair again. |
| Magic devices | Run `python3 omagic.py revert-trackpad` from the checkout if you applied its trackpad profile. Remove any optional Fn helper through its documented upstream process. |
| AirPlay | Stop mirroring. Use the widget to forget receivers and remove plugin-created firewall rules if desired. Source removal leaves DoubleTake and Avahi installed. |
| Messages | Follow upstream cleanup for local shims, SSH configuration, and remote Mac tools. Source removal does not remove that bridge. |
| Calendar | Restore your previous clock after disabling OmaCal. Account credentials remain local. |
| Activity Monitor | Remove any optional privileged helper through its upstream instructions. |

Generated build output, source edits, added local branches, and stashes make source removal refuse. Preserve those artifacts outside the checkout, complete backend cleanup, and resolve the reported differences before retrying. In particular, archive the AirPods build directory after using its install manifest; do not discard the manifest to satisfy a clean-tree check.

Remove plugins installed with `--with-shadows` before uninstalling the shared desktop module, or migrate their panels back to upstream styling first.
