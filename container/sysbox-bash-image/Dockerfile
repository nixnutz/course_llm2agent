# Sysbox system container: Ubuntu Jammy + systemd + inner Docker (Slice 1 lab).
# Build from repository root: docker build -f container/sysbox-bash-image/Dockerfile .
# ENTRYPOINT ["/sbin/init"] from base — do not override. Compose must not set init: true.
FROM nestybox/ubuntu-jammy-systemd-docker:latest

COPY container/sysbox-bash-image/scripts/ /usr/local/lib/sysbox-bash/
COPY container/sysbox-bash-image/systemd/ /etc/systemd/system/
COPY container/sysbox-bash-image/app/ /opt/sysbox-bash-app/

RUN chmod +x /usr/local/lib/sysbox-bash/*.sh /usr/local/lib/sysbox-bash/lib/*.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv \
    && python3 -m venv /opt/sysbox-bash-venv \
    && /opt/sysbox-bash-venv/bin/pip install --no-cache-dir -r /opt/sysbox-bash-app/requirements.txt \
    && systemctl mask ssh.service ssh.socket 2>/dev/null || true \
    && passwd -l admin 2>/dev/null || true \
    && ln -sf /etc/systemd/system/sysbox-bash-load-exec-image.service \
        /etc/systemd/system/multi-user.target.wants/sysbox-bash-load-exec-image.service \
    && ln -sf /etc/systemd/system/sysbox-bash-api.service \
        /etc/systemd/system/multi-user.target.wants/sysbox-bash-api.service \
    && rm -rf /var/lib/apt/lists/*
