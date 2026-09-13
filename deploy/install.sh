#!/bin/bash
# install.sh
#
# One-time setup on a freshly cloned Pi: system dependencies, a venv,
# email_config.py, and the autostart systemd service. Safe to re-run later
# (e.g. after requirements.txt changes) -- it only creates what's missing
# and otherwise just refreshes the venv/service.
#
# Usage (from the repo root, after `git clone`):
#   ./deploy/install.sh
#
# See deploy/README.md for the full first-time setup (auto-login, etc.).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${SUDO_USER:-$USER}"
APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"

echo "Repo dir : $REPO_DIR"
echo "App user : $APP_USER"
echo "App home : $APP_HOME"

echo
echo "==> Installing system dependencies (apt)"
# Runtime libs Kivy's SDL2 window/input providers link against on Linux
# (kivy[base] does NOT bundle these on Linux the way it does on
# Windows/macOS -- they must come from apt), plus GL/mtdev for the
# touchscreen. If a package name below doesn't exist on your Raspberry Pi
# OS version, check https://kivy.org/doc/stable/installation/installation-rpi.html
# for the current list and adjust.
sudo apt-get update
sudo apt-get install -y \
    python3-venv python3-pip python3-dev git \
    libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0 libsdl2-ttf-2.0-0 \
    libmtdev1 libgl1 libgles2 fonts-freefont-ttf

echo
echo "==> Creating/updating the virtualenv"
python3 -m venv "$REPO_DIR/venv"
"$REPO_DIR/venv/bin/pip" install --upgrade pip
"$REPO_DIR/venv/bin/pip" install -r "$REPO_DIR/requirements.txt"

echo
echo "==> email_config.py"
if [ -f "$REPO_DIR/email_config.py" ]; then
    echo "Already exists, leaving it alone."
else
    cp "$REPO_DIR/email_config.example.py" "$REPO_DIR/email_config.py"
    echo "Created from email_config.example.py -- edit it with real SMTP"
    echo "credentials before relying on the POSLAŤ button:"
    echo "    nano $REPO_DIR/email_config.py"
fi

echo
echo "==> Installing the autostart service"
sed \
    -e "s#__REPO_DIR__#$REPO_DIR#g" \
    -e "s#__USER__#$APP_USER#g" \
    -e "s#__HOME__#$APP_HOME#g" \
    "$REPO_DIR/deploy/galanda.service.template" | sudo tee /etc/systemd/system/galanda.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable galanda.service
sudo systemctl restart galanda.service

echo
echo "==> Done."
echo "Status : systemctl status galanda.service"
echo "Logs   : journalctl -u galanda.service -f"
echo
echo "If the app doesn't come up on the touchscreen after a reboot, make"
echo "sure desktop auto-login is enabled: sudo raspi-config -> System"
echo "Options -> Boot / Auto Login -> Desktop Autologin. See deploy/README.md."
