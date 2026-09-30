# Source setup inventory

Audited on September 30, 2026. This records the source machine, not a promise that every feature is installed by this repository.

| Area | Source implementation | Distribution in this starter |
| --- | --- | --- |
| Light desktop | Local Apple-inspired theme, original Silver Coast wallpaper, Inter font | Core desktop assets, renamed `mac-starter` |
| Corners | Window radius 12, rounding power 4 | Core Lua |
| Frosted panels | White at 0.75 alpha; blur size 8, two passes, xray off | Core TOML and Lua |
| Shadows | Window shadow range 24; panel blur 22, black alpha 0.16, downward offset 5 | Core Lua and QML wrappers |
| Spacing | Inner gap 1; outer top 1, other sides 2 | Core Lua |
| Day/time | OmaCal at far right, `dddd h:mm AP` | Existing calendar reused; supplied clock otherwise |
| Shortcuts | Selected Super-to-Ctrl application shortcuts with terminal exceptions | Core shortcuts module |
| Gestures | Natural scrolling; bounded three-finger workspace swipes | Core shortcuts module |
| Smart zoom | Two two-finger taps toggle 1×/2× compositor magnification; selected touchpad | Documented, hardware selection not automated |
| Magic Mouse | Modified v1.1.3 daemon/plugin with custom tuning | Pinned optional module plus patches and tuning example |
| AirPods | Omapods v1.3.6 with matching modified LibrePods daemon | Pinned optional module and setup guide |
| AirPlay | Mirror plugin v0.2.0 plus DoubleTake | Pinned optional module with timeout fix |
| Magic Keyboard/Trackpad | OMagic v1.0.0 | Pinned optional module; helper setup remains optional |
| Calendar | OmaCal v1.0.2 with HEY CLI | Pinned optional module and account setup guide |
| iMessage/contacts | Blip v2.6.2 over SSH to a Mac | Pinned optional module and bridge setup guide |
| Activity Monitor | v2.1.1 with panel styling | Pinned optional module |
| Notes | icloud-md v0.6.2, local vault | Documentation only |
| iPhone webcam | OBS and DroidCam; virtual camera | Documentation only |
| Face unlock | Howdy, custom lock plugin, Dell infrared driver adaptations | Hardware-specific documentation only |
| Other custom panels | Podcasts, VPN, notification links/history, critical battery warning, app overlays | Inventory and future extraction scope |
| Other installed tools | LocalSend, Sushi, Omasnap, Voxtype | Documentation of existing tools |
| BlueFerry | Source checkout v0.7.7 | Experiment only; not claimed active |

During the audit, Magic Mouse and LibrePods services were running but their devices reported disconnected. AirPlay mirroring and OBS were not running. Blip connectivity and account synchronization were not exercised. The current desktop had no Hyprland configuration errors.

Installed copies of the old clock, old face-unlock plugin, and a menu clone were disabled. Backups and browser-extension experiments were not treated as current behavior. No private application data or device state was exported.
