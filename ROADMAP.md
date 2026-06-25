# Roadmap

## Hardening / debug
- [ ] Remove machine-specific paths/hardcodes (sink names are detected dynamically — double-check none remain).
- [x] i18n with locale detection (ES/EN).
- [ ] Test on a clean machine (no prior `~/.config/anthrophonic/`).
- [ ] Handle edge cases: no BT, no HDMI, BT disconnecting mid-playback.
- [ ] Clear errors if `numpy`, `paplay` or `pw-dump` is missing.
- [ ] Check for leaks: stray `paplay` processes from the pulse on close / on failure.

## Packaging
- [x] `install.sh` (dependency check + `.desktop` install).
- [x] `docs/panel.png` screenshot for the README.
- [ ] Custom icon instead of `audio-volume-high`.

## Future ideas
- [ ] Remember `extra` per BT device (MAC) for multiple headsets.
- [ ] Per-display HDMI sync (several TVs).
- [ ] Tray icon mode.
- [ ] Package as Flatpak or `.deb`.
