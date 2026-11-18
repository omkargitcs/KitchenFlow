#!/bin/bash
set -euxo pipefail

dnf install -y python3.11 python3.11-pip git
cd /opt
git clone ${repo_url} kitchenflow
cd kitchenflow
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed

cat > /etc/systemd/system/kitchenflow.service <<UNIT
[Unit]
Description=KitchenFlow API
After=network.target

[Service]
WorkingDirectory=/opt/kitchenflow
Environment=API_KEY=${api_key}
ExecStart=/opt/kitchenflow/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=always
User=root

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now kitchenflow
