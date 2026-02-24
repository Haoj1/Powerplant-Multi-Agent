# AWS EC2 Deployment Guide

Deploy the Multi-Agent Powerplant Monitoring System on AWS EC2 using the public IP (no domain required).

## Prerequisites on EC2

- **OS**: Ubuntu 22.04 LTS (or similar)
- **Docker**: For MQTT (Mosquitto)
- **Python 3.11+**: With venv
- **Node.js 18+**: For building frontend (optional, if serving UI)

## 1. EC2 Setup

### Launch Instance

- AMI: Ubuntu 22.04 LTS
- Instance type: t3.small or larger
- Storage: 20 GB+
- **Security Group**: Allow inbound TCP:
  - **8005** – Agent D (API + frontend) – main entry
  - **8001** – Simulator (optional, if direct access needed)
  - **22** – SSH
  - **1883** – MQTT (only if external clients connect)

### Connect

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
```

## 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in for docker group

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Node.js (for frontend build)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3. Deploy Project

```bash
# Clone or upload project
cd ~
git clone <your-repo-url> multi-agent-project
cd multi-agent-project

# Python venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy and edit .env
cp .env.example .env
nano .env   # Set MQTT_HOST=127.0.0.1, API keys, etc.
```

## 4. Build Frontend (Optional)

To serve the web UI from Agent D:

```bash
cd agent-review/frontend
npm install
npm run build
cd ../..
```

This creates `agent-review/frontend/dist/`. Agent D will serve it at `http://<EC2_IP>:8005`.

## 5. Start Backend

```bash
chmod +x scripts/start_backend_ec2.sh
./scripts/start_backend_ec2.sh
```

This starts:

- MQTT (Docker)
- Simulator (8001)
- Agent A (8002)
- Agent B (8003)
- Agent C (8004)
- Agent D (8005)

## 6. Access

- **Web UI** (if frontend built): `http://<EC2_PUBLIC_IP>:8005`
- **API only**: `http://<EC2_PUBLIC_IP>:8005/api/...`
- **Simulator**: `http://<EC2_PUBLIC_IP>:8001`

## 7. Stop Backend

```bash
./scripts/stop_backend_ec2.sh
```

## 8. Run on Boot (Optional)

Using systemd:

```bash
sudo nano /etc/systemd/system/multi-agent.service
```

```ini
[Unit]
Description=Multi-Agent Powerplant Backend
After=network.target docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=ubuntu
WorkingDirectory=/home/ubuntu/multi-agent-project
ExecStart=/home/ubuntu/multi-agent-project/scripts/start_backend_ec2.sh
ExecStop=/home/ubuntu/multi-agent-project/scripts/stop_backend_ec2.sh

[Install]
WantedBy=multi-user.target
```

Or use a process manager like `supervisord` for long-running processes.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| ECONNREFUSED 127.0.0.1:8001 | Simulator not running; check `logs/simulator.log` |
| MQTT connection failed | `docker compose up -d mosquitto` |
| Port already in use | `./scripts/stop_backend_ec2.sh` then restart |
| CORS errors | Agent D has `allow_origins=["*"]`; ensure you use the correct EC2 IP |
| Frontend 404 | Run `npm run build` in `agent-review/frontend` |
