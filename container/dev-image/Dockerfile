FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        python3 \
        python3-pip \
        sudo \
        python3-venv \
        curl \
        nano \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.in /tmp/requirements.in
COPY container/dev-image/scripts/bootstrap-project-venv.sh /usr/local/bin/bootstrap-project-venv.sh
COPY container/dev-image/scripts/import-local-ca.sh /usr/local/bin/import-local-ca.sh
COPY container/dev-image/scripts/keepalive.sh /usr/local/bin/keepalive.sh
COPY container/dev-image/scripts/start-notebook.sh /usr/local/bin/start-notebook.sh

RUN python3 -m venv "${VIRTUAL_ENV}" \
    && "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir --upgrade pip \
    && "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir -r /tmp/requirements.in \
    && groupadd --gid 1000 dev \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash dev \
    && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && chmod 0440 /etc/sudoers.d/dev \
    && mkdir -p /workspace \
    && chown -R dev:dev /workspace \
    && chmod +x /usr/local/bin/bootstrap-project-venv.sh /usr/local/bin/import-local-ca.sh /usr/local/bin/keepalive.sh /usr/local/bin/start-notebook.sh \
    && rm -f /tmp/requirements.in

WORKDIR /workspace
USER dev
CMD ["/usr/local/bin/keepalive.sh"]
