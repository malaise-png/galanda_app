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

If the display was rotated to portrait at the OS level (raspi-config /
Control Centre -> Screens, not something this repo scripts), touch input
often does NOT rotate along with it -- this is a known gap in the
labwc/Wayland desktop (current default on Raspberry Pi OS), not an app
bug. Symptom: taps land offset from where you actually touched, and
dragging feels jumpy/erratic because the drag math is working across
mismatched axes.

Fix it with a libinput calibration matrix, applied via udev rule so it's
independent of any app or window manager:

1. Find the exact touch device name:
   ```
   libinput list-devices
   ```
   (install with `sudo apt-get install -y libinput-tools` if missing).
   Look for the touch monitor's entry and note its exact `Device:` name.
2. Create `/etc/udev/rules.d/90-touch-rotate.rules`:
   ```
   SUBSYSTEM=="input", ATTRS{name}=="<exact device name from step 1>", ENV{LIBINPUT_CALIBRATION_MATRIX}="0 -1 1 1 0 0"
   ```
   That matrix (from libinput's own documentation) is for a 90 clockwise
   rotation -- use `-1 0 1 0 -1 1` for 180, or `0 1 0 -1 0 1` for 270
   clockwise (90 counter-clockwise), matching whatever direction you
   rotated the screen.
3. `sudo udevadm control --reload-rules && sudo reboot`, then re-test.

A pure rotation matrix assumes the touch sensor's active area lines up
exactly with the visible screen edge-to-edge. On a large overlay touch
panel there's often a real mechanical/wiring offset on top of that -- on
this kiosk's **iiyama ProLite TF3215MC (eGalax P81X84 controller)**,
after the 90 clockwise rotation above the touchscreen's Y axis came out
inverted (confirmed by touching the screen's actual top-left corner and
seeing `libinput debug-events --device <path>` report it near the
*bottom*-left instead). The corrected matrix for this exact unit is:
```
0 -1 1 -1 0 1
```
If you're setting up a *different* Pi/touchscreen and see something
similar (taps land offset, buttons only respond in the wrong spot,
dragging feels erratic even after the plain rotation matrix), diagnose it
the same way rather than assuming the matrix above applies:
1. `sudo libinput debug-events --device <your device's /dev/input/eventN>`
   (from `libinput list-devices`).
2. Touch dead-center of the screen once, then the screen's actual
   top-left corner once -- note the two `TOUCH_DOWN` percentages printed
   for each.
3. Compare against what those two touches *should* have reported
   (roughly 50/50 for center, 0/0 for top-left in libinput's percentage
   convention). A consistent inversion on one axis only (as above) means
   swap that axis's sign and offset in the matrix; a consistent
   scale/shift on both points suggests an offset/scale error instead.
   Send the two measured pairs along with which matrix is currently
   active if you want help computing the correction.

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
