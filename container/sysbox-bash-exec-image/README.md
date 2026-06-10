# Sysbox Bash exec image

Per-session Bash/Python execution image loaded into the **inner** Docker daemon of `sysbox_bash`.

Built on the host and exported to `container/compose/.state/sysbox_bash/images/sysbox-bash-exec-image.tar` by `make sysbox-bash-image-build`.

## Build (usually via Make)

```bash
make sysbox-bash-image-build
```

Default tag: `course-llm-sysbox-bash-exec:dev` (`SBASH_EXEC_IMAGE_NAME`).
