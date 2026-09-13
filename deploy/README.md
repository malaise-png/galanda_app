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
