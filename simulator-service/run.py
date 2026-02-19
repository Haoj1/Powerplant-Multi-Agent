#!/usr/bin/env python3
"""
Launch script for simulator service.

This script sets up the Python path to allow imports from shared_lib.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now import and run main
from simulator_service.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
