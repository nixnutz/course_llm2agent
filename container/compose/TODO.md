# TODO

## Infrastructure

### High

- Keep insecure default credentials/placeholders under review and consider enforcing a startup guard for unchanged defaults.
- Keep container/image version pinning under review to reduce drift from floating tags.
- Revisit `FORWARDED_ALLOW_IPS=*` hardening strategy if exposure model changes.

### Medium

- Review/harden telemetry endpoint:
  - OTLP collector traffic in this setup currently runs without TLS (local/dev network).
  - Decide whether OTLP should stay internal to the Docker network only, or be additionally exposed with TLS termination.
  - If host exposure is required, add AuthN/AuthZ and rate limits in front of the telemetry endpoint.
- Avoid runtime package installation in one-shot init containers (`apk add ...`) by using prebuilt helper images.
- Default `store_prompts_in_spend_logs` to `false` in `config/litellm.yaml` and document temporary enabling for debugging.
- Add a trace attribution checklist for agent experiments (for example `service.name`, env, version, agent identifier).

### Low

- Add a `make doctor` preflight check for local setup dependencies and port conflicts.

## Course

- No open course-specific TODOs yet.

## Other / Experiments

### Low

- ADR: define archive mechanics for superseded summaries (`docs/auto-doc/adr/archive/` flow and move criteria).
- ADR: define a pre-review sync routine from raw log to active ADR summaries.
