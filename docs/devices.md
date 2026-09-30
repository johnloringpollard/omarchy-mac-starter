# Configure your plugins

Run `./setup` to install the plugins you want. After installation, use their panels and upstream guides for configuration. Device pairing, personal preferences, accounts, and connections to other computers are yours to choose.

| Plugin | Configure after installation | Upstream guide |
| --- | --- | --- |
| Magic Mouse | Pair the mouse and adjust pointer, scrolling, and gestures. | [Magic Mouse for Omarchy](https://github.com/maikunari/omarchy-magic-mouse#readme) |
| AirPods | Pair your AirPods and choose supported listening modes. | [Omapods](https://github.com/thisisgm/omarchy-pods#readme) |
| AirPlay | Select a receiver, pair if needed, and choose a screen to share. | [AirPlay Mirror](https://github.com/ETroll/omarchy-airplay#readme) |
| Magic Keyboard/Trackpad | Connect devices and choose function-key or trackpad preferences. The privileged Fn helper is optional. | [OMagic](https://github.com/betnbd/Omagic#readme) |
| Calendar | Connect your calendar, then enable OmaCal in place of your existing clock. It is installed without enabling a second clock. | [OmaCal](https://github.com/crmne/omacal#readme) |
| Messages | Connect Blip to a reachable Mac signed into Messages. Its bridge setup runs separately. | [Blip](https://github.com/nixfred/blip#readme) |
| Activity Monitor | Choose the panel options you want. The privileged power-reading helper is optional. | [Activity Monitor](https://github.com/stappmus/omarchy-activity-monitor#readme) |

AirPlay sends the Linux desktop to a compatible receiver; it does not receive an iPhone screen. OMagic does not provide Touch ID. AirPods use the plugin's matching daemon, not an arbitrary LibrePods build.

## Advanced installation

`./setup` is the normal installation path. The lower-level tool supports individual source installs and explicit inspection:

```bash
./plugins list
./plugins install magic-mouse
./plugins install magic-mouse --apply --with-shadows
```

The lower-level `plugins` command installs source only. Unlike `setup`, it does not install packages or backend daemons. Exact revisions and patches are in `dependencies.lock.json`.

Do not run `omarchy plugin update` on starter-managed patched checkouts. That bypasses the reviewed revision and local patches. Preserve your edits before changing an installed source version.

## Removal

Complete upstream backend cleanup before removing its source checkout. The starter's plugin removal disables the widget and removes only an unchanged checkout. It preserves packages, device rules, services, pairing information, and account data, and saves the latest widget settings locally.

| Plugin | Cleanup before removing the checkout |
| --- | --- |
| Magic Mouse | Run its `uninstall.sh` and follow the upstream removal instructions. |
| AirPods | Stop/disable `librepods.service`. Use `daemon/build/install_manifest.txt` to identify installed files. Keep that manifest until cleanup is complete. |
| Magic Keyboard/Trackpad | Revert an applied trackpad profile and remove the optional Fn helper through the upstream instructions if you installed it. |
| AirPlay | Stop mirroring. Forget receivers or remove plugin-created firewall rules if you want to. DoubleTake and Avahi remain installed. |
| Messages | Follow upstream cleanup for local shims, SSH configuration, and any remote Mac tools you configured. |
| Calendar | Restore your previous clock after disabling OmaCal. |
| Activity Monitor | Remove any optional privileged helper through its upstream instructions. |

Then preview and remove the source checkout:

```bash
./plugins remove magic-mouse
./plugins remove magic-mouse --apply
```

Removal refuses generated build output, source edits, added branches, or stashes. Preserve those outside the checkout and complete backend cleanup before retrying. Archive the AirPods build directory after using its install manifest; do not discard the manifest just to satisfy the clean-tree check.

Remove shadow-enabled plugins before uninstalling the shared desktop module, or migrate their panels back to upstream styling first. If you configured a different clock after core installation, restore the previous clock identity before core uninstall so it can restore its recorded settings.
