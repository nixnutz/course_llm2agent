# Sysbox Bash exec image

Per-session execution image loaded into the **inner** Docker daemon of `sysbox_bash`.

Built on the host and exported to `container/compose/.state/sysbox_bash/images/sysbox-bash-exec-image.tar` by `make sysbox-bash-image-build`.

## TODO / gap — name says “Bash”, runtime is Python-based

**Naming is misleading today.** Paths, service names, and the LangGraph tool surface use
`bash` / `sysbox-bash`, but this image is built `FROM python:3.11-bookworm`. Bash is only the
`sandbox` user shell; **Python 3.11 is always present** in every session container.

**Why it matters (lab honesty):**

- Security reviews and course prose must not assume “Bash-only” execution.
- `make sysbox-bash-api-smoke` **depends on Python inside the session** (network probes via
  `python3` + `socket`; stdout/stderr limit checks via `python -c`). A future minimal
  Bash-only exec image would break those smokes unless rewritten (e.g. `curl`, `/dev/tcp`).
- LLM-generated Python in session scripts is already possible today — not a hypothetical.

**Deferred (no fix in current slice):** rename to neutral wording, split Bash vs Python exec
images, or document an explicit “allowed interpreters” contract in ADR/API.

## Build (usually via Make)

```bash
make sysbox-bash-image-build
```

Default tag: `course-llm-sysbox-bash-exec:dev` (`SBASH_EXEC_IMAGE_NAME`).
