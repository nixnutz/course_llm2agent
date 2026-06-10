# Sysbox Bash service image

Sysbox **system container** for the `sysbox_bash` Compose service: systemd (PID 1) plus inner Docker.

This is **not** the per-session exec image (`container/sysbox-bash-exec-image/`).

## Build

From repository root:

```bash
make sysbox-bash-image-build
```

Requires Docker on the host. The Compose service also requires `sysbox-runc` (see `container/compose/scripts/sysbox_bash/preflight.sh`).

## Spike verification (Slice 1)

| Spike | Check |
|-------|--------|
| S0 | `docker compose exec sysbox_bash systemctl is-active docker.service` → `active` |
| S1 | `docker compose exec sysbox_bash docker run --rm hello-world` |
| S2 | `docker compose exec sysbox_bash docker images` shows exec image tag |
| S3 | `GET http://sysbox_bash:8080/health` → 200 |

## Environment variable naming

Compose service name: `sysbox_bash`. Container env uses **`SBASH_*`** (not `SYSBOX_*`) because the Sysbox runtime reserves `SYSBOX_` names for its own configuration.

## Compose constraints

- `runtime: sysbox-runc` on the host
- **Do not** set `init: true` on this service — systemd must remain PID 1
- No `entrypoint` / `command` overrides

## Troubleshooting

```bash
docker compose exec sysbox_bash systemctl status docker.service
docker compose exec sysbox_bash systemctl status sysbox-bash-load-exec-image.service
docker compose exec sysbox_bash systemctl status sysbox-bash-api.service
docker compose exec sysbox_bash journalctl -u sysbox-bash-load-exec-image.service --no-pager
docker compose exec sysbox_bash journalctl -u sysbox-bash-api.service --no-pager
```
