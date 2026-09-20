from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import mimetypes
import re

from .config import ROOT, settings
from . import database as db
from . import service

WEB = (ROOT / "app" / "web").resolve()

class Handler(BaseHTTPRequestHandler):
    server_version = "VerticePrototype/1.0"

    def log_message(self, fmt, *args):
        print(f"[HTTP] {self.address_string()} {fmt % args}")

    def send_json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(payload)

    def body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Corpo muito grande")
        return json.loads(self.rfile.read(length).decode("utf-8") or "{}")

    def error_json(self, exc):
        status = 403 if isinstance(exc, PermissionError) else 400 if isinstance(exc, (ValueError, json.JSONDecodeError)) else 500
        self.send_json({"error": str(exc) if status != 500 else "Erro interno"}, status)

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path
            if path == "/api/bootstrap":
                return self.send_json(service.bootstrap())
            if path == "/api/client/conversations":
                return self.send_json(service.list_for_customer(query.get("customer_id", [""])[0]))
            if path == "/api/operator/conversations":
                return self.send_json(service.list_for_actor(query.get("actor_id", [""])[0]))
            match = re.fullmatch(r"/api/client/conversations/([A-Za-z0-9-]+)", path)
            if match:
                return self.send_json(service.get_for_customer(query.get("customer_id", [""])[0], match.group(1)))
            match = re.fullmatch(r"/api/operator/conversations/([A-Za-z0-9-]+)", path)
            if match:
                return self.send_json(service.get_for_actor(query.get("actor_id", [""])[0], match.group(1)))
            return self.static(path)
        except Exception as exc:
            self.error_json(exc)

    def do_POST(self):
        try:
            path, body = urlparse(self.path).path, self.body()
            if path == "/api/client/conversations":
                return self.send_json(service.create(body["customer_id"], body.get("channel", "Canal Vértice"), body["text"]), 201)
            match = re.fullmatch(r"/api/client/conversations/([A-Za-z0-9-]+)/messages", path)
            if match:
                return self.send_json(service.client_message(body["customer_id"], match.group(1), body["text"]))
            match = re.fullmatch(r"/api/operator/conversations/([A-Za-z0-9-]+)/messages", path)
            if match:
                return self.send_json(service.operator_message(body["actor_id"], match.group(1), body["text"]))
            match = re.fullmatch(r"/api/operator/conversations/([A-Za-z0-9-]+)/status", path)
            if match:
                return self.send_json(service.change_status(body["actor_id"], match.group(1), body["status"]))
            if path == "/api/reset":
                if body.get("actor_id") != "gestor-01":
                    raise PermissionError("Somente a gestora pode restaurar a demonstração")
                db.reset_db(); return self.send_json({"ok": True})
            return self.send_json({"error": "Rota não encontrada"}, 404)
        except Exception as exc:
            self.error_json(exc)

    def static(self, path):
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (WEB / relative).resolve()
        if not target.is_relative_to(WEB) or not target.is_file():
            target = WEB / "index.html"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(target)[0] or "application/octet-stream") + ("; charset=utf-8" if target.suffix in {".html", ".css", ".js"} else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(data)

def main():
    db.init_db()
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    print(f"Vértice disponível em http://{settings.host}:{settings.port}")
    print("IA:", "configurada" if service.configured() else "fallback local")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
