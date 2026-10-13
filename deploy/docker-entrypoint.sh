#!/bin/sh
set -eu

if [ "${#FOXPROFILE_API_TOKEN}" -lt 24 ]; then
    echo "FOXPROFILE_API_TOKEN must have at least 24 characters." >&2
    exit 1
fi
if [ "${#FOXPROFILE_VNC_PASSWORD}" -ne 8 ]; then
    echo "FOXPROFILE_VNC_PASSWORD must have exactly 8 characters (VNC limit)." >&2
    exit 1
fi
mkdir -p /data/profiles /data/logs /data/exchange "$HOME/.vnc"
umask 077
x11vnc -storepasswd "$FOXPROFILE_VNC_PASSWORD" "$HOME/.vnc/passwd" >/dev/null 2>&1
# A recreated container has no live display, but the writable layer may retain locks.
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
exec /usr/bin/supervisord -c /etc/foxprofile-supervisord.conf
