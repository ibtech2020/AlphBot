#!/usr/bin/env python3
"""
Entry point for the trading bot service.
Starts the gunicorn webhook server in a background subprocess, then runs
the main trading bot loop in the foreground.
"""

import os
import sys
import time
import subprocess

# ========== START WEBHOOK SERVER ==========
def start_webhook_server():
    """Launch gunicorn serving webhook_server:app on 0.0.0.0:8000."""
    working_dir = os.path.dirname(os.path.abspath(__file__))
    process = subprocess.Popen(
        [
            sys.executable, "-m", "gunicorn",
            "--workers", "1",
            "--bind", "0.0.0.0:8000",
            "webhook_server:app",
        ],
        cwd=working_dir,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print("🌐 Webhook server started on port 8000 (POST /webhook)")
    return process


webhook_process = start_webhook_server()

# Give gunicorn a moment to bind before the bot starts logging
time.sleep(2)

# ========== START TRADING BOT ==========
# Import triggers module-level initialisation (exchange setup, print statements)
# and then enters the main while-loop defined at module scope.
import sma_strategy  # noqa: F401, E402
