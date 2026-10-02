# Explore macOS apps with VibeDarling

[VibeDarling](https://github.com/VibeDarling/darling) is a development fork of
[Darling](https://github.com/darlinghq/darling), a compatibility layer for running
macOS software on Linux without a macOS virtual machine. The “Vibe” refers to
vibe coding: AI coding agents are the project's primary development tools,
alongside contributor testing and review.

This is an experimental integration option for people who want to help bring
macOS applications to their Linux desktop. It is a separate runtime project,
not an Omarchy panel plugin. The starter's `./setup`, `./plugins`, and
`./uninstall` commands do not install, update, or remove VibeDarling.

## Compatibility snapshot

As of October 2, 2026, VibeDarling contributors report roughly **9–10 stock macOS
apps running**, including **TextEdit, Stickies, and Terminal**. They also report
**iTerm2** working. These are reports from their development environments, not
results of a fresh Omarchy installation tested by this starter. Compatibility
varies with the app version, architecture, runtime revision, and workflow.

**iMessage compatibility is a development target.** Successful account sign-in,
activation, and sending or receiving messages through VibeDarling have not been
established here. The starter's existing [Messages plugin](devices.md) uses Blip
with a reachable Mac signed into Messages; VibeDarling is not currently a
replacement for that bridge.

The runtime is still rough, but its contributors feel the progress shows promise
toward supporting potentially most macOS programs over time. This is an
aspiration, not a promise that a particular app or Apple service will work.

## Try it separately from the desktop setup

1. Read VibeDarling's [development notes](https://github.com/VibeDarling/darling/blob/master/CLAUDE.md)
   and [known issues](https://github.com/VibeDarling/darling/blob/master/known-issues.md).
   Check the architecture and runtime requirements for the app you want to test.
2. Follow that project's source-build guidance, including its pinned submodules
   and Swift Git LFS inputs. Check its [releases](https://github.com/VibeDarling/darling/releases)
   for available artifacts; source-only entries are not installable binary packages.
   Original Darling packages do not necessarily contain VibeDarling's changes.
3. Use the documented staged-runtime procedure and a disposable Darling prefix
   for experiments. Keep the runtime's install manifest and follow its own cleanup
   instructions; the starter cannot undo a manual runtime installation.
4. Record the exact app version, CPU architecture, VibeDarling revision and
   submodule pins, Omarchy environment, reproduction commands, and observed
   behavior. Test an actual workflow, including exit and relaunch, rather than
   treating an open window as full compatibility.

Automated installation through this starter would need a reproducible runtime
build or package, a reviewed revision, and verified install, update, and removal
behavior on the supported Omarchy baseline. This guide is a starting point for
that work, not a claim that those checks have passed.

## Help move it forward

**VibeDarling is looking for more contributors.** Useful contributions include
reproducible application tests, Darwin and framework compatibility fixes,
graphics and input work, Arch/Ubuntu packaging, and clearer setup documentation.
iMessage is one of the longer-term compatibility goals contributors can help
investigate.

Start with the project's [issues](https://github.com/VibeDarling/darling/issues)
and [contribution protocol](https://github.com/VibeDarling/darling/blob/master/.claude/ISSUE_COLLABORATION.md).
Coordinate work there, keep the applications under test unmodified, and report
installation, launch, and usable-workflow results separately. Improvements to
Omarchy-specific setup and desktop integration can be proposed to this starter.
