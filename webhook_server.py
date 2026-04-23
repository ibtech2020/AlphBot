#!/usr/bin/env python3
"""
Webhook server for the trading bot.
Runs on port 8000 in a background thread, accepting POST requests at /webhook.
Validates the WEBHOOK_SECRET header before processing any payload.
"""

import os
import json
import logging
import threading
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
    """Start the Flask webhook server in a daemon thread on port 8000."""
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False),
        daemon=True,
        name="webhook-server",
    )
    thread.start()
    print("🌐 Webhook server started on port 8000 (POST /webhook)")
    return thread
