"""Simple HTTP server for the backtest UI."""
import http.server
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
handler = http.server.SimpleHTTPRequestHandler
server = http.server.HTTPServer(("localhost", 8080), handler)
print("Serving at http://localhost:8080/ui.html")
server.serve_forever()
