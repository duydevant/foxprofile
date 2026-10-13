"""Integration checks against the running Docker stack (no extra test packages).

    docker compose exec foxprofile python deploy/docker-smoke.py

Creates disposable profiles, tests both real engines, then removes test data.
"""

import asyncio
import json
import os
import socket
import threading
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = "http://127.0.0.1:8000"
TOKEN = os.environ["FOXPROFILE_API_TOKEN"]


def request(path, method="GET", data=None, authenticated=True):
    headers = {"Content-Type": "application/json"}
    if authenticated:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=150) as response:
        body = response.read()
        return json.loads(body) if "json" in response.headers.get("Content-Type", "") else body


class Fixture(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"""<html><title>Docker smoke</title><body><input id="field"><button id="go" onclick="document.querySelector('#result').textContent=document.querySelector('#field').value">Go</button><p id="result">ready</p></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


async def check_mcp():
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(
        BASE + "/mcp", headers={"Authorization": f"Bearer {TOKEN}"}
    ) as (reader, writer, _):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            available = await session.list_tools()
            assert any(tool.name == "list_profiles" for tool in available.tools)
            result = await session.call_tool("list_profiles", {})
            assert not result.isError, result
            print(f"PASS MCP initialize, {len(available.tools)} tools, list_profiles")


def main():
    assert request("/api/v1/health")["success"]
    assert b"html" in request("/").lower()
    try:
        request("/api/v1/profiles", authenticated=False)
        raise AssertionError("Unauthenticated profiles request was accepted")
    except urllib.error.HTTPError as error:
        assert error.code == 401
    with urllib.request.urlopen("http://127.0.0.1:6080/vnc.html") as response:
        assert response.status == 200
    with socket.create_connection(("127.0.0.1", 5900), timeout=5) as connection:
        assert connection.recv(12).startswith(b"RFB ")
    print("PASS panel, health, API authentication, noVNC, VNC server")

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{fixture.server_port}/"
    try:
        for engine in ("camoufox", "chrome"):
            name = f"docker-smoke-{engine}-{uuid.uuid4().hex[:8]}"
            profile_path = f"/api/v1/profiles/{name}"
            browser_path = f"/api/v1/browser/{name}"
            archive = None
            created = False
            try:
                request("/api/v1/profiles", "POST", {
                    "name": name, "engine": engine, "os_type": "linux",
                    "timezone": "Asia/Ho_Chi_Minh", "locale": "vi-VN",
                })
                created = True
                launched = request(browser_path + "/launch", "POST")
                assert launched["success"] and "started" in launched["message"].lower(), launched
                request(browser_path + "/page/navigate", "POST", {"url": url})
                request(browser_path + "/page/type", "POST", {"selector": "#field", "text": "Docker OK"})
                request(browser_path + "/page/click", "POST", {"selector": "#go"})
                rendered = request(browser_path + "/page/text?selector=%23result")
                assert "Docker OK" in json.dumps(rendered), rendered
                png = request(browser_path + "/page/screenshot")
                assert png.startswith(b"\x89PNG"), "Invalid screenshot"
                request(browser_path + "/page/evaluate", "POST", {
                    "script": "document.cookie='docker_smoke=retained; Max-Age=3600; path=/'",
                })
                request(browser_path + "/stop", "POST")
                cookies = request(profile_path + "/cookies?format=json")
                assert "docker_smoke" in json.dumps(cookies), cookies
                fingerprint = request(profile_path + "/fingerprint")
                assert fingerprint["exists"], fingerprint
                exported = request(profile_path + "/export", "POST", {"export_dir": "/data/exchange", "include_data": True})
                assert exported["success"], exported
                archive = Path(exported["zip_path"])
                assert archive.is_file()
                request(profile_path, "DELETE")
                created = False
                imported = request("/api/v1/profiles/import", "POST", {"zip_path": str(archive)})
                assert imported["success"], imported
                created = True
                assert "docker_smoke" in json.dumps(request(profile_path + "/cookies?format=json"))
                print(f"PASS {engine}: create, launch, navigate, type, click, screenshot, cookies, fingerprint, ZIP export/import")
            finally:
                if created:
                    try:
                        if request(browser_path + "/status")["is_running"]:
                            request(browser_path + "/stop", "POST")
                    finally:
                        request(profile_path, "DELETE")
                if archive:
                    archive.unlink(missing_ok=True)
                for partial in Path("/data/exchange").glob(f"{name}_*.zip"):
                    partial.unlink()
        asyncio.run(check_mcp())
    finally:
        fixture.shutdown()
    print("All Docker smoke checks passed.")


if __name__ == "__main__":
    main()
