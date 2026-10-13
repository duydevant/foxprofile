FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    HOME=/home/foxprofile \
    DISPLAY=:99

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv ca-certificates curl \
    xvfb x11-utils x11vnc novnc websockify openbox supervisor \
    libgtk-3-0t64 libgtk-4-1 libasound2t64 libnss3 libnspr4 \
    libdbus-1-3 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 \
    libcups2t64 libdrm2 libgbm1 libx11-xcb1 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libxrender1 libxtst6 libxt6 libxshmfence1 \
    libegl1 libgl1 libpci3 libpulse0 libgdk-pixbuf-2.0-0 libsecret-1-0 \
    dbus-x11 zenity xdg-utils \
    fonts-liberation fonts-dejavu-core fonts-noto-core fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && useradd --create-home --uid 10001 --shell /bin/bash foxprofile

WORKDIR /app
COPY requirements.txt .
COPY deploy/requirements-docker.txt ./deploy/requirements-docker.txt
RUN pip install --no-cache-dir -r deploy/requirements-docker.txt && pip check
COPY --chown=foxprofile:foxprofile chrome_engine ./chrome_engine
RUN mkdir -p /data/profiles /data/logs /data/exchange \
    && mkdir -p /opt/venv/lib/python3.12/site-packages/fpgen/data \
    && chown -R foxprofile:foxprofile /data /app /opt/venv/lib/python3.12/site-packages/fpgen/data

USER foxprofile
# Fetch both engines and GeoIP ahead of time so first launch is ready.
RUN python -m camoufox fetch official/stable/156.0.1-beta.36 && python -m chrome_engine fetch

# Application changes do not invalidate the large browser download layer.
COPY --chown=foxprofile:foxprofile src ./src
COPY --chown=foxprofile:foxprofile foxprofile_mcp.py .
COPY deploy/docker-entrypoint.sh /usr/local/bin/foxprofile-entrypoint
COPY deploy/supervisord.conf /etc/foxprofile-supervisord.conf
COPY deploy/docker-start-app.sh /usr/local/bin/foxprofile-start-app
USER root
RUN chmod +x /usr/local/bin/foxprofile-entrypoint /usr/local/bin/foxprofile-start-app \
    && apt-get update && apt-get install -y --no-install-recommends tzdata-legacy pcmanfm \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/flet \
    && tar -xzf /opt/venv/lib/python3.12/site-packages/flet_desktop/app/flet-linux-amd64.tar.gz -C /opt/flet
ENV FLET_VIEW_PATH=/opt/flet/flet
USER foxprofile
COPY --chown=foxprofile:foxprofile deploy/docker-smoke.py ./deploy/docker-smoke.py
COPY --chown=foxprofile:foxprofile deploy/docker-healthcheck.py ./deploy/docker-healthcheck.py

EXPOSE 8000 6080
ENTRYPOINT ["foxprofile-entrypoint"]
