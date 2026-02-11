# Installation Commands

## Required Python Packages

Run these commands to install all required dependencies:

```bash
# Core web framework
pip install fastapi>=0.104.1
pip install uvicorn[standard]>=0.24.0

# Data validation
pip install pydantic>=2.5.0
pip install pydantic-settings>=2.1.0

# MQTT client
pip install paho-mqtt>=1.6.1

# HTTP client
pip install httpx>=0.25.0

# Environment variables
pip install python-dotenv>=1.0.0

# Numerical computation (required for simulator)
pip install numpy>=1.26.0
```

## Or install all at once:

```bash
pip install fastapi uvicorn pydantic pydantic-settings paho-mqtt httpx python-dotenv numpy
```

## Or use requirements.txt:

```bash
pip install -r requirements.txt
```

## Verify Installation

Check if packages are installed:

```bash
python3 -c "import fastapi, uvicorn, pydantic, paho.mqtt, httpx, numpy; print('All packages installed successfully')"
```

## Start MQTT Broker

```bash
docker-compose up -d mosquitto
```

## Test MQTT Connection

```bash
# Publish a test message
mosquitto_pub -h localhost -p 1883 -t test -m "hello"

# Subscribe to see messages
mosquitto_sub -h localhost -p 1883 -t "test" -v
```

## Run Simulator

```bash
# From project root directory
cd simulator-service
python3 main.py
```

The simulator will start on `http://localhost:8001`
