# Virtual Environment Setup Guide

## Quick Setup

### Linux / macOS

```bash
# Run the setup script
./setup_venv.sh
```

### Windows

```cmd
# Run the setup script
setup_venv.bat
```

## Manual Setup

### Linux / macOS

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt
```

### Windows

```cmd
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
venv\Scripts\activate.bat

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt
```

## Using the Virtual Environment

### Activate

**Linux / macOS:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate.bat
```

### Deactivate

```bash
deactivate
```

## Verify Installation

After activating the virtual environment, verify all packages are installed:

```bash
python3 -c "import fastapi, uvicorn, pydantic, paho.mqtt, httpx, numpy; print('✅ All packages installed successfully')"
```

## Running the Simulator

With the virtual environment activated:

```bash
cd simulator-service
python3 main.py
```

## Troubleshooting

### Python version

Make sure you have Python 3.11 or higher:

```bash
python3 --version
```

### Permission errors (Linux/macOS)

If you get permission errors, make sure the script is executable:

```bash
chmod +x setup_venv.sh
```

### Virtual environment not found

If the venv directory doesn't exist, create it manually:

```bash
python3 -m venv venv
```
