import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "q-vercel-latency.json").read_text(encoding="utf-8"))


def percentile(values, q):
    """Linear-interpolation percentile (same as numpy's default)."""
    s = sorted(values)
    if not s:
        return 0.0
    pos = (len(s) - 1) * q
    lo = int(pos)
    frac = pos - lo
    return s[lo] + frac * (s[lo + 1] - s[lo]) if lo + 1 < len(s) else s[lo]


def region_stats(region, threshold):
    rows = [r for r in DATA if r["region"] == region]
    lat = [r["latency_ms"] for r in rows]
    up = [r["uptime_pct"] for r in rows]
    n = len(rows) or 1
    return {
        "region": region,
        "avg_latency": round(sum(lat) / n, 2),
        "p95_latency": round(percentile(lat, 0.95), 2),
        "avg_uptime": round(sum(up) / n, 3),
        "breaches": sum(1 for x in lat if x > threshold),
    }


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Expose-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        regions = body.get("regions", [])
        threshold = float(body.get("threshold_ms", 180))
        result = {"regions": [region_stats(r, threshold) for r in regions]}
        out = json.dumps(result).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        out = b'{"status": "ok", "usage": "POST {\\"regions\\": [...], \\"threshold_ms\\": 180}"}'
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(out)
