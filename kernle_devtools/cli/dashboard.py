"""Dashboard CLI command handler."""

import logging
import webbrowser
from http.server import HTTPServer

from kernle_devtools.dashboard.server import DashboardHandler

logger = logging.getLogger(__name__)


def cmd_dashboard(args, k):
    """Launch the web dashboard."""
    port = getattr(args, "port", 8420)
    host = getattr(args, "host", "127.0.0.1")
    no_open = getattr(args, "no_open", False)

    DashboardHandler.kernle_instance = k

    server = HTTPServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}"
    logger.info("Dashboard running at %s", url)
    print(f"Dashboard running at {url}")

    if not no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        server.shutdown()
