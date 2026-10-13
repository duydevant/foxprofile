"""Check the API, remote desktop and native UI when desktop mode is enabled."""

import os
import socket
import urllib.request
from pathlib import Path


def desktop_running():
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if (process / "comm").read_text().strip() == "flet":
                stat = (process / "stat").read_text()
                if stat[stat.rindex(")") + 2 :].split()[0] != "Z":
                    return True
        except OSError:
            continue
    return False


for url in ("http://127.0.0.1:8000/api/v1/health", "http://127.0.0.1:6080/vnc.html"):
    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
with socket.create_connection(("127.0.0.1", 5900), timeout=3) as connection:
    assert connection.recv(12).startswith(b"RFB ")
if os.environ.get("FOXPROFILE_MODE", "desktop") == "desktop":
    assert desktop_running(), "Flet desktop is not running"
