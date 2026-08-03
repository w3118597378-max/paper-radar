"""本地验证服务器：静态文件 + /api/arxiv 代理（模拟 Cloudflare Pages Function）。

用法: python dev_server.py [port]
"""
import http.server
import socketserver
import urllib.request
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
ARXIV = "https://export.arxiv.org/api/query"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/arxiv"):
            target = ARXIV + ("?" + self.path.split("?", 1)[1] if "?" in self.path else "")
            try:
                req = urllib.request.Request(target, headers={"User-Agent": "paper-radar-demo/0.1"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                    self.send_response(resp.status)
                    self.send_header("Content-Type", "application/atom+xml; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
            except Exception as e:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(str(e).encode())
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


with socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"Serving on http://127.0.0.1:{PORT}")
    httpd.serve_forever()
