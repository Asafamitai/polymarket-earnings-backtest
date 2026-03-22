"""Production-ready HTTP server for the backtest UI."""
import http.server
import json
import logging
import os
import signal
import sys
from functools import partial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8080))
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


class CORSHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with CORS, caching headers, and JSON content-type."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        # Cache static assets, don't cache JSON data
        if self.path.endswith(".json"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        elif self.path.endswith((".html", ".css", ".js")):
            self.send_header("Cache-Control", "public, max-age=300")
        super().end_headers()

    def do_GET(self):
        # Redirect root to calendar
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/calendar.html")
            self.end_headers()
            return
        super().do_GET()

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")


def run_server():
    os.chdir(PROJECT_DIR)

    server = http.server.HTTPServer((HOST, PORT), CORSHandler)

    # Graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("Shutting down server...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info(f"Server starting on http://{HOST}:{PORT}")
    logger.info(f"  Calendar: http://localhost:{PORT}/calendar.html")
    logger.info(f"  Backtest: http://localhost:{PORT}/ui.html")
    logger.info(f"  Serving from: {PROJECT_DIR}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped.")
        server.server_close()


if __name__ == "__main__":
    run_server()
