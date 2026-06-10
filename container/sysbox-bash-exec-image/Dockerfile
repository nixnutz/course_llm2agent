FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 1001 sandbox \
    && useradd --uid 1001 --gid sandbox --create-home --shell /bin/bash sandbox \
    && mkdir -p /sandbox \
    && chown sandbox:sandbox /sandbox

WORKDIR /sandbox
USER sandbox
CMD ["sleep", "infinity"]
