# Deploying to the Raspberry Pi kiosk

How the dev-mode toggle and autostart fit together, one-time setup on a new
Pi, and the everyday "edit on Windows -> push -> update the Pi" loop.

## How it works

- `theme.DEV_MODE` (see `theme.py`) is driven by the `GALANDA_KIOSK` env
  var, not a flag you edit by hand. Unset (your Windows laptop) ->
  `DEV_MODE = True` (windowed, resizable, mouse multitouch simulator).
  `GALANDA_KIOSK=1` (set by the systemd service below) -> `DEV_MODE =
  False` (true fullscreen kiosk).
- That means whatever `DEV_MODE` says in the committed code doesn't
  matter for the Pi -- the service always forces kiosk mode. You never
  need to flip it before/after pushing.
- `galanda.service` (installed by `install.sh` from
  `galanda.service.template`) starts the app on boot, sets
  `GALANDA_KIOSK=1`, and restarts it automatically if it ever crashes.

## First-time setup on a new Pi

1. Flash Raspberry Pi OS (with Desktop) and boot it.
2. `sudo raspi-config` -> *System Options* -> *Boot / Auto Login* ->
   **Desktop Autologin**. Required: the service waits for the desktop's
   graphical session and needs a display already up (see the unit
   template's comments) -- without auto-login there's no session for it
   to attach to.
3. Clone the repo and run the installer:
   ```
   git clone https://github.com/malaise-png/galanda_app.git ~/galanda_app
   cd ~/galanda_app
   chmod +x deploy/install.sh deploy/update.sh
   ./deploy/install.sh
   ```
   This installs system packages, creates `venv/`, installs Python deps,
   seeds `email_config.py` from the example template (fill in real SMTP
   credentials afterwards -- see the comments in that file), and installs
   + enables the autostart service.
4. `sudo reboot`. The app should come up fullscreen on the touchscreen
   after the desktop loads.

## Connecting over SSH

1. **Enable SSH on the Pi** (skip if you already turned it on in Raspberry
   Pi Imager's advanced/gear-icon options when flashing the SD card):
   ```
   sudo raspi-config
   ```
   *Interface Options* -> *SSH* -> **Enable**. Or non-interactively:
   `sudo systemctl enable --now ssh`.
2. **Find the Pi's address.** On the Pi itself: `hostname -I`. From
   Windows, you can usually skip the IP and just use the mDNS hostname
   instead: `raspberrypi.local` (or `<hostname-you-set>.local` if you gave
   it a custom hostname in Imager) -- Windows 10/11 resolves `.local`
   names out of the box.
3. **Connect from a Windows PowerShell prompt** (OpenSSH client is
   built in, no install needed):
   ```
   ssh pi@raspberrypi.local
   ```
   Replace `pi` with whatever username you set -- Raspberry Pi Imager
   makes you choose a username/password per-image now, there's no default
   `pi`/`raspberry` login anymore on a fresh flash. The first connection
   asks you to confirm the host key fingerprint (type `yes`); after that
   it just prompts for the password.
4. **Optional: passwordless login**, handy since the everyday workflow
   below SSHes in every time you push a change:
   ```
   ssh-keygen -t ed25519                                   # if you don't already have a key
   type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh pi@raspberrypi.local "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
   ```
   After that, `ssh pi@raspberrypi.local` connects without a password
   prompt.

Everywhere else in this doc, `pi@<pi-address>` means whatever
`<user>@<hostname-or-ip>` you land on from these steps.

## Everyday workflow: edit on Windows, update the Pi

1. Work on Windows as usual -- `python main.py` runs windowed
   (`DEV_MODE` defaults to `True` there since `GALANDA_KIOSK` is unset).
2. Commit and push to GitHub from Windows.
3. On the Pi, pull and restart in one step:
   ```
   ssh pi@<pi-address> "~/galanda_app/deploy/update.sh"
   ```
   (or SSH in first and run `./deploy/update.sh` from the repo root).

Only run `deploy/install.sh` again if `requirements.txt` changed or the
service file needs updating -- `update.sh` is just `git pull` + restart.

## Useful commands on the Pi

```
systemctl status galanda.service       # is it running?
journalctl -u galanda.service -f       # live logs
sudo systemctl stop galanda.service    # stop the kiosk (e.g. for maintenance)
sudo systemctl start galanda.service   # start it again without a reboot
```

There's no exit button or Escape shortcut in the app itself (by design,
it's a kiosk) -- use `systemctl stop` over SSH when you need to get to a
desktop/terminal on the Pi itself.

## Touchscreen: rotated screen but misaligned/jumpy touch

**Key fact, found the hard way**: this app does NOT get its touch input
through SDL2/Wayland/libinput on this kiosk. `journalctl -u
galanda.service` shows Kivy's own built-in Linux touch auto-detection
(`kivy/config.py` unconditionally sets `Config.setdefault("input",
"%(name)s", "probesysfs...")` on Linux) reading `/dev/input/eventN`
directly via its `mtdev` provider -- confirmed because *removing* that
provider (to try to stop what looked like duplicate touches) left the
app with no working touch at all. SDL2 does register as an input
provider too (`auto add sdl2 input provider` in the log, and Xwayland is
involved -- see the `xinput` warnings), but it isn't what's actually
driving touches into the app.

This matters a lot for troubleshooting: **a libinput/udev-level fix (a
`LIBINPUT_CALIBRATION_MATRIX` rule, `xinput`, etc.) has NO EFFECT on this
app**, no matter how correct, because libinput never sees this data path
-- it's a completely different code path read straight from the kernel
device. The fix has to happen in `main.py`'s `Config.set("input", ...)`
line instead, via `mtdev`'s own `rotation`/`invert_x`/`invert_y`
parameters (documented in `kivy/input/providers/mtdev.py`, passed through
`probesysfs`'s `param=` syntax -- see that file's docstring).

If the display is rotated to portrait at the OS level (raspi-config /
Control Centre -> Screens) and touches land wrong or dragging misbehaves,
diagnose and fix it at the mtdev layer:

1. Find the exact `/dev/input/eventN` path: `libinput list-devices` (or
   `cat /proc/bus/input/devices`) -- still useful just to identify the
   device, even though libinput itself doesn't matter here.
2. Get 2+ known reference touches to solve for the right parameters
   rather than guessing: watch `journalctl -u galanda.service -f` isn't
   useful for per-touch coordinates, so instead temporarily add a print
   of `touch.sx, touch.sy` somewhere touch-handling runs (e.g. the top of
   `CanvasArea.on_touch_down` in `canvas_widgets.py`), redeploy, tap
   dead-center and then the screen's actual top-left corner, and read the
   two `(sx, sy)` pairs back from `journalctl`. Remove the print
   afterwards.
3. Work out the right `rotation`/`invert_x`/`invert_y` combination from
   `mtdev.py`'s own coordinate logic (`assign_coord` in that file) against
   those two points, the same way `rotation=90` (no inversion) was solved
   for **this kiosk's iiyama ProLite TF3215MC (eGalax P81X84
   controller)** -- see the current line in `main.py`:
   ```
   Config.set("input", "%(name)s", "probesysfs,provider=mtdev,param=rotation=90")
   ```
   `rotation` only takes 0/90/180/270; if the axes come out swapped or
   mirrored on top of a rotation that's otherwise close, add
   `param=invert_x=1` and/or `param=invert_y=1` (comma-separated, each
   its own `param=` entry) and re-derive from the same two data points.

A `LIBINPUT_CALIBRATION_MATRIX` udev rule was set up earlier for this
device (see git history) before this was understood -- it's harmless to
leave in place (it just calibrates a pipeline this app doesn't use) but
isn't doing anything for this app's touch behavior.

Separately, `theme.TOUCH_JITTER_DISTANCE` (used in `main.py`, kiosk mode
only) filters out small raw-coordinate noise this kind of commodity USB
touch panel tends to report even when held still, so a steady touch
doesn't read as a tiny unintended drag. Increase it a bit if dragging
still feels jittery after fixing the rotation above; keep it small enough
that quick, precise taps still register cleanly.

`canvas_widgets.py`'s `DraggableImage.on_touch_down` also rejects any new
touch landing within `theme.GHOST_TOUCH_MIN_SEPARATION` pixels of one
already being tracked, since this eGalax controller occasionally reports
a spurious near-duplicate second contact point for a single real finger
-- Kivy's Scatter treats any two simultaneous touches as a rotate/scale
gesture, and two nearly-coincident points make that gesture's angle
calculation wildly unstable (a plain one-finger drag would suddenly
rotate or resize). Raise that constant if genuine two-finger gestures
ever misfire as noise (unlikely -- real fingers start much farther apart
than the default), or lower it if single-finger drags still glitch.
