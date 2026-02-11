"""Dashboard HTTP server — serves API endpoints and HTML dashboard."""

import dataclasses
import json
import logging
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def serialize(obj):
    """Convert kernle dataclasses/objects to JSON-serializable dicts."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (list, tuple)):
        return [serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: serialize(v) for k, v in dataclasses.asdict(obj).items()}
    return str(obj)


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    kernle_instance = None  # Set by server setup

    def log_message(self, format, *args):
        logger.info(format, *args)

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status, message):
        self._send_json({"error": message}, status)

    def _get_int_param(self, params, key, default):
        try:
            vals = params.get(key, [])
            return int(vals[0]) if vals else default
        except (ValueError, IndexError):
            return default

    def _get_bool_param(self, params, key):
        """Return True, False, or None if not specified."""
        vals = params.get(key, [])
        if not vals or vals[0] == "":
            return None
        return vals[0].lower() in ("true", "1", "yes")

    def do_GET(self):  # noqa: N802
        from kernle_devtools.dashboard.templates import DASHBOARD_HTML

        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query, keep_blank_values=True)
        k = self.__class__.kernle_instance

        try:
            if path == "" or path == "/":
                return self._send_html(DASHBOARD_HTML)

            elif path == "/api/stats":
                stats = k.stack.get_stats()
                return self._send_json(serialize(stats))

            elif path == "/api/anxiety":
                report = k.get_anxiety_report(detailed=True)
                return self._send_json(serialize(report))

            elif path == "/api/raw":
                limit = self._get_int_param(params, "limit", 200)
                processed = self._get_bool_param(params, "processed")
                entries = k.stack.list_raw(processed=processed, limit=limit)
                return self._send_json(serialize(entries))

            elif m := re.match(r"^/api/raw/([^/]+)$", path):
                raw_id = m.group(1)
                entry = k.stack.get_raw(raw_id)
                if entry is None:
                    return self._send_error(404, "Not found")
                return self._send_json(serialize(entry))

            elif path == "/api/episodes":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_episodes(limit=limit, include_forgotten=True, include_weak=True)
                return self._send_json(serialize(items))

            elif path == "/api/beliefs":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_beliefs(limit=limit, include_forgotten=True, include_weak=True)
                return self._send_json(serialize(items))

            elif path == "/api/values":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_values(limit=limit, include_forgotten=True, include_weak=True)
                return self._send_json(serialize(items))

            elif path == "/api/goals":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_goals(limit=limit, include_forgotten=True, include_weak=True)
                return self._send_json(serialize(items))

            elif path == "/api/notes":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_notes(limit=limit, include_forgotten=True, include_weak=True)
                return self._send_json(serialize(items))

            elif path == "/api/relationships":
                items = k.stack.get_relationships()
                return self._send_json(serialize(items))

            elif path == "/api/drives":
                items = k.stack.get_drives()
                return self._send_json(serialize(items))

            elif path == "/api/suggestions":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_suggestions(limit=limit)
                return self._send_json(serialize(items))

            elif path == "/api/processing":
                config = k.stack.get_processing_config()
                return self._send_json(serialize(config))

            elif m := re.match(r"^/api/provenance/(\w+)/([^/]+)$", path):
                mem_type, mem_id = m.group(1), m.group(2)
                valid_types = {
                    "raw", "episode", "belief", "value", "goal",
                    "note", "drive", "relationship",
                }
                if mem_type not in valid_types:
                    return self._send_error(400, "Invalid memory type")
                derived = k.stack.get_memories_derived_from(mem_type, mem_id)
                result = [{"type": t, "id": i} for t, i in derived]
                return self._send_json(result)

            elif path == "/api/audit":
                limit = self._get_int_param(params, "limit", 100)
                items = k.stack.get_audit_log(limit=limit)
                return self._send_json(serialize(items))

            elif path == "/api/settings":
                settings = k.stack.get_all_stack_settings()
                return self._send_json(serialize(settings))

            else:
                return self._send_error(404, "Not found")

        except Exception:
            logger.exception("Error handling %s", path)
            return self._send_error(500, "Internal server error")
