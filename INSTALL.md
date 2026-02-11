# Installation Instructions

## Required Python Packages

Install the following packages manually (choose the method that works for your environment):

### Option 1: Install from requirements.txt

```bash
pip install -r requirements.txt
```

### Option 2: Install packages individually

```bash
# Core dependencies
pip install fastapi>=0.104.1
pip install uvicorn[standard]>=0.24.0
pip install pydantic>=2.5.0
pip install pydantic-settings>=2.1.0

# MQTT
pip install paho-mqtt>=1.6.1

# HTTP client
pip install httpx>=0.25.0

# Utilities
pip install python-dotenv>=1.0.0

# Numerical computation (required for simulator)
pip install numpy>=1.26.0
```

### Option 3: Using conda (if you prefer conda)

```bash
conda install numpy
pip install fastapi uvicorn pydantic pydantic-settings paho-mqtt httpx python-dotenv
```

## Python Version

Requires Python 3.11 or higher.

Check your Python version:
```bash
python3 --version
```

## Environment Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - MQTT broker host and port
   - (Optional) GitHub token for ticket creation

## MQTT Broker Setup

Start Mosquitto using Docker Compose:

```bash
docker-compose up -d mosquitto
```

Or install Mosquitto locally and start it manually.

## Verify Installation

Run the test script:

```bash
python3 test_phase0.py
```

This will check if all dependencies are installed correctly.

## Troubleshooting

### Import errors

If you get import errors, make sure you're in the project root directory and Python can find the modules:

```bash
# Add project root to PYTHONPATH (Linux/Mac)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run from project root
cd "/path/to/Multi-Agent Project"
python3 simulator-service/main.py
```

### MQTT connection errors

If MQTT connection fails:
1. Check if Mosquitto is running: `docker ps | grep mosquitto`
2. Check MQTT settings in `.env`
3. Test connection: `mosquitto_pub -h localhost -p 1883 -t test -m "hello"`
