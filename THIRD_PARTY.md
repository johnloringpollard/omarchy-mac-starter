# Credits and licenses

Original installer code, documentation, the local theme, and local patches are released under the root MIT license, subject to the upstream notices below.

| Component | Source | Notice |
| --- | --- | --- |
| Omarchy-derived panel clones, popup component, and theme conventions | [Omarchy](https://github.com/omacom/omarchy), source system package 4.0.4-1 | [MIT, David Heinemeier Hansson](licenses/omarchy-MIT.txt) |
| Inter 4.1 font | [Inter](https://github.com/rsms/inter/releases/tag/v4.1) | [SIL Open Font License](assets/fonts/LICENSE.txt) |
| Light/dark palettes, Coastal Curves wallpapers, and appearance scheduler | [Omarchy Mac Style, commit 1b26d92](https://github.com/johnloringpollard/omarchy-mac-style/tree/1b26d921cce44a3293928cbee9fbad1ab4f8da0b) | Root MIT license; scheduler adapted for starter-owned names and activation |
| Tokyo Night terminal palette | [Folke Lemaitre](https://github.com/folke/tokyonight.nvim) | [Apache 2.0 notice](licenses/TokyoNight-LICENSE.txt) |
| Silver Coast wallpaper | Original SVG and PNG from the local Apple-inspired theme | Root MIT license; editable source at `assets/silver-coast.svg` |
| Magic Mouse patch | [maikunari/omarchy-magic-mouse](https://github.com/maikunari/omarchy-magic-mouse) | [Upstream MIT notice](licenses/magic-mouse-MIT.txt) |
| AirPlay patch | [ETroll/omarchy-airplay](https://github.com/ETroll/omarchy-airplay) | [Upstream MIT notice](licenses/airplay-MIT.txt) |
| Omapods panel patch | [thisisgm/omarchy-pods](https://github.com/thisisgm/omarchy-pods) | [Widget MIT notice](licenses/airpods-MIT.txt) |
| Activity Monitor panel patch | [stappmus/omarchy-activity-monitor](https://github.com/stappmus/omarchy-activity-monitor) | [Upstream MIT notice](licenses/activity-monitor-MIT.txt) |
| OMagic | [betnbd/Omagic](https://github.com/betnbd/Omagic) | MIT, fetched separately |
| OmaCal | [crmne/omacal](https://github.com/crmne/omacal) | MIT, fetched separately |
| Blip | [nixfred/blip](https://github.com/nixfred/blip) | MIT, fetched separately |

Exact dependency revisions are recorded in `dependencies.lock.json`. Their full source and notices are fetched from upstream at installation time. No upstream daemon binaries are bundled.

Omapods contains two separately licensed components: its widget is MIT, while its modified LibrePods daemon is GPL-3.0. Follow the daemon's license when redistributing it. Omapods also explicitly excludes its Apple product outlines from the MIT grant. This starter does not vendor those outlines. Apple's SF fonts and SF Symbols are not included.

Brand artwork retained inside the Omarchy-derived agents panel belongs to its respective owners. Its inclusion does not imply endorsement. Apple device and product names identify compatibility targets; Apple does not sponsor this project.
