#!/bin/bash
# update.sh
#
# Run this on the Pi (over SSH) after pushing new commits from Windows, to
# pull them and restart the kiosk with the new code:
#
#   ssh pi@<pi-address> "~/galanda_app/deploy/update.sh"
#
# Only pulls + restarts -- it does NOT touch email_config.py (gitignored,
# untouched by git pull) or re-run the apt/venv setup. Re-run
# deploy/install.sh instead if requirements.txt changed.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Pulling latest changes"
git pull --ff-only

echo
echo "==> Restarting galanda.service"
sudo systemctl restart galanda.service

echo
echo "==> Done. Status:"
sleep 2
systemctl status galanda.service --no-pager -l
