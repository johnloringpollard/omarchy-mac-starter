# Keyboard and trackpad reference

On an Apple keyboard, the Command key normally maps to `Super`. Confirm the mapping in your keyboard configuration.

| Shortcut | Behavior |
| --- | --- |
| Super+A | Select all. Ghostty receives its Ctrl+Shift+A shortcut. |
| Super+Z | Undo in desktop applications. Suppressed in tagged terminals. |
| Super+Shift+Z | Redo in desktop applications. Suppressed in tagged terminals. |
| Super+T | New tab. Ghostty receives Ctrl+Shift+T. |
| Super+Shift+T | Reopen a closed browser tab. Suppressed in terminals. |
| Super+R | Reload a page. Suppressed in terminals. |
| Super+Alt+T | Toggle floating/tiling. This replaces the stock Super+T window action. |
| Three-finger horizontal swipe | Move one workspace at a time without creating new workspaces. |
| Two-finger scrolling | Natural scrolling. |

The shortcut module explicitly unbinds these keys before registering replacements. Removing the module and reloading Hyprland restores the underlying configuration. Review `modules/shortcuts.lua` if you have assigned these keys yourself.

Omarchy already supplies Super+C/V/X clipboard shortcuts and Super+Space for its launcher. Super+W still closes a window, and Super+Tab still changes workspaces. This preset does not implement all macOS application-switching or text-navigation behavior.

The source machine also uses two-finger double-tap magnification, function-row sound keys, and Super+I for Omasnap. Those are documented extensions rather than defaults here. Magnification needs a selected touchpad device so it does not consume mouse buttons from every pointing device.
