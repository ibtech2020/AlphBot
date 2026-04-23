#!/usr/bin/env python3
"""
Webhook server for the trading bot.
Runs on port 8000 via gunicorn (subprocess), accepting POST requests at /webhook.
Validates the WEBHOOK_SECRET header before processing any payload.
"""

import os
import json
import logging
import subprocess
import sys
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Accepts incoming webhook payloads.
    Requires the Authorization header to match the WEBHOOK_SECRET env var.
    Returns 401 if the secret is missing or incorrect, 200 on success.
    """
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "")

    # Validate secret from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not webhook_secret or auth_header != webhook_secret:
        logger.warning("Webhook received with invalid or missing Authorization header")
        return jsonify({"error": "Unauthorized"}), 401

    # Parse and log the payload
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}

    logger.info(f"Webhook received: {json.dumps(payload)}")
    print(f"📡 Webhook received: {json.dumps(payload)}")

    return jsonify({"status": "ok", "message": "Webhook received"}), 200


def start_webhook_server():
    """Start the Flask webhook server via gunicorn in a background subprocess on port 8000."""
    process = subprocess.Popen(
        [
            sys.executable, "-m", "gunicorn",
            "--workers", "1",
            "--bind", "0.0.0.0:8000",
            "webhook_server:app",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("🌐 Webhook server started on port 8000 (POST /webhook)")
    return process
