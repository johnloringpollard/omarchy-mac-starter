# Set up other Mac-like conveniences

These integrations were found on the source machine. They are documented options, not automatic parts of the core installer.

## iCloud Notes

The source setup uses [icloud-md](https://github.com/coddingtonbear/icloud-md) 0.6.2 through a Node environment. It requires Node 20 or newer and Playwright. Follow its upstream installation and login instructions, choose a new local vault directory, and test an explicit fetch before enabling any write workflow.

This is an explicit fetch/push workflow, not continuous synchronization. Browser sessions, account profiles, the Notes vault, and sync metadata are excluded from the starter.

## iPhone as a webcam

Install OBS and the [DroidCam OBS plugin](https://github.com/dev47apps/droidcam-obs-plugin) using their supported instructions. Configure the iPhone source locally, create an OBS profile and scene collection named `iPhone Camera`, and start OBS's virtual camera. Select that virtual camera in your video-call application.

The source machine uses 1920×1080 at 60 fps. Choose resolution and frame rate for your network and device. Its saved source contains device identifiers and network addresses, so that OBS scene is not bundled. Its virtual-camera device number is also machine-specific.

Once your profile works, the equivalent launcher is:

```bash
obs --profile "iPhone Camera" --collection "iPhone Camera" --scene "Camera" --startvirtualcam
```

## Sharing, previews, screenshots, and dictation

LocalSend provides local file transfers. Sushi provides file previews in Nautilus. Omasnap provides region screenshots. Voxtype provides dictation. These were installed on the source machine and overlap with stock Omarchy capabilities; inspect your installation before adding packages.

The source keyboard also binds F10/F11/F12 to mute/down/up and Super+I to Omasnap. Add these only after checking your existing function-key and Super bindings.

## Face unlock

The source machine uses a custom Howdy integration with a Dell XPS infrared camera and locally adapted HM1092/IPU drivers. That implementation is tied to its hardware, kernel, and authentication configuration. It is not shipped as a generic installer.

Use a maintained integration compatible with your camera, enroll locally, and retain working password authentication. Test a covered camera, cancellation, failed recognition, and password fallback. Never copy another machine's PAM configuration, biometric models, or camera drivers as a desktop preset.

## Other local plugins

The source desktop has custom podcast playback, NetworkManager VPN controls, browser-aware notifications, low-battery alerts, and X/Spotify popup launchers. These are listed in the inventory for future extraction. They are not bundled here because they need their own configuration, behavior checks, and maintenance boundaries.

BlueFerry was present only as a source checkout. It was not found as an installed application or running service and is not included as a verified integration.
