# Configuration ownership

`setup` is the normal entrypoint. It selects optional plugins, installs their prerequisites and required local backends, and activates the desktop preset. Pairing, account setup, receiver selection, and the optional remote Mac bridge remain with the user and upstream plugins.

The lower-level tools have two installation boundaries.

`install` manages user configuration through `scripts/starter.py`. Each journal operation owns a file, Lua block, TOML value, JSON value, widget identity, or clock position. It records both the prior value and installed value before applying changes. Repeating an interrupted operation converges on those recorded values. A later conflicting edit stops the operation before its planned changes begin.

The core `install` command installs a separate `mac-starter` theme and appends explicit Lua includes to `hyprland.lua`. It does not invoke theme hooks or restart the desktop. `setup` performs theme activation and the reload after that core step succeeds. The legacy Apple theme hook is detected before applying changes because it restored an entire historical bar layout and could discard later additions.

Stock panel copies use the `macstarter.*` namespace. Only corresponding stock widgets already in the bar are replaced. Existing custom widgets, including OmaCal, retain their identities and settings. The supplied panel copies are tied to the documented Omarchy baseline and need review after shell API changes.

`plugins` manages pinned third-party source checkouts through `scripts/plugins.py`. Its lock file names a full commit and checksum for each local patch. Functional patches apply by default. Optional shadow patches require the core's shared QML components. Checkout receipts record file content and modes so removal can distinguish a managed patch from a later edit.

Both tools serialize mutations with `~/.local/state/omarchy-mac-starter/operation.lock`. Plugin receipts and the core journal are separate. The `--home` option supports temporary-home verification. Plugin staging with `--home` never calls the live Omarchy shell.

`setup` installs required packages and invokes the pinned Magic Mouse and AirPods backend installers. Root-owned device rules and daemons still have upstream removal procedures. Removing a widget is not sufficient to undo them.

On subsequent runs, `setup` leaves completed core installations and configured plugins alone. Private setup state records the original theme, pending plugin enablement, and completed backend work so an interrupted installation can resume. New plugins use shared shadows when the desktop components are installed. It never runs Blip's remote Mac setup, HEY authentication, Bluetooth pairing, or optional privileged helpers.

## Update policy

Update a dependency by reviewing its upstream changes, updating its full commit and version, regenerating patches against that commit, and updating patch checksums. Fetch it in an isolated home and run its applicable tests before publishing the new lock file.

Do not run `omarchy plugin update` on starter-managed patched checkouts. That bypasses the lock and may overwrite or conflict with the local patches. Preserve local edits and uninstall the source checkout before installing a different selection.

Do not publish a home-directory snapshot. New exports must use an explicit file allowlist and pass `scripts/check_export.py`. Keep device identities, credentials, caches, logs, and installation journals local.
