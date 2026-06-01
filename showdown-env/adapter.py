"""
HTTP adapter — exposes your env via the BenchAnything four-endpoint protocol.

Local dev:
    python adapter.py
    python adapter.py --port 9000
"""
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from env import ShowdownEnv

env = ShowdownEnv()

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            if self.path == "/reset":
                obs = env.reset()
                self._respond({"observation": obs, "done": False})
            elif self.path == "/step":
                length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(length))
                obs, reward, done = env.step(body["action"])
                self._respond({"observation": obs, "reward": reward, "done": done})
            elif self.path == "/close":
                self._respond({"status": "closed"})
        except Exception as e:
            print(f"ERROR on {self.path}: {e}")
            traceback.print_exc()
            self._respond({"error": str(e)}, status=500)

    def do_GET(self):
        if self.path == "/health":
            self._respond({"status": "ok"})

    def _respond(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[{self.path}] {format % args}")
HTTPServer(('0.0.0.0', 8765), Handler).serve_forever()
