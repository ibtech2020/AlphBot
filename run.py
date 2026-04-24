#!/usr/bin/env python3
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from sma_strategy import main as run_bot

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"AlphBot running")

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # suppress access logs

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    # Run bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # HTTP server on main thread so Railway doesn't 502
    print(f"🌐 Health server on port {port}")
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
