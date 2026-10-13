#!/bin/sh
set -eu
until xdpyinfo >/dev/null 2>&1; do sleep 1; done
case "${FOXPROFILE_MODE:-desktop}" in
    desktop) exec dbus-run-session -- python -m src.main ;;
    server) exec python -m src.server ;;
    *) echo "FOXPROFILE_MODE must be desktop or server" >&2; exit 1 ;;
esac
