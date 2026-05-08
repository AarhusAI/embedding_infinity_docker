"""Tiny bearer-token validator used by nginx auth_request.

Reads /keys/api_keys.txt on every request so add/revoke is live without restart.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

KEYS_FILE = Path("/keys/api_keys.txt")
BIND_HOST = "0.0.0.0"
BIND_PORT = 8000


def load_keys() -> dict[str, str]:
    if not KEYS_FILE.exists():
        return {}
    keys: dict[str, str] = {}
    for line in KEYS_FILE.read_text().splitlines():
        token_part, sep, comment = line.partition("#")
        token = token_part.strip()
        if not token:
            continue
        keys[token] = comment.strip() if sep else ""
    return keys


def extract_token(header_value: str) -> str:
    value = (header_value or "").strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return ""


class Handler(BaseHTTPRequestHandler):
    def _verify(self) -> None:
        token = extract_token(self.headers.get("X-Original-Authorization", ""))
        client_ip = self.headers.get("X-Real-IP", "-")
        path = self.headers.get("X-Original-URI", "-")
        keys = load_keys()
        if token and token in keys:
            label = keys[token] or "-"
            self.send_response(204)
            print(f"204 {client_ip} {path} {label}", flush=True)
        else:
            sent = token or "-"
            self.send_response(401)
            print(f"401 {client_ip} {path} {sent}", flush=True)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path.startswith("/verify"):
            self._verify()
        elif self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        self.do_GET()

    def log_message(self, format: str, *args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler).serve_forever()
