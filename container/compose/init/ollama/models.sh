#!/bin/sh
set -eu
# Purpose: preload or validate configured Ollama models at stack startup.
# Called by: one-shot container service "ollama_init_models".
# Notes: behavior is controlled by OLLAMA_INIT_MODE and related env vars.

MODELS_DEFAULT="nomic-embed-text:latest llama3.2:3b"
MODELS="${OLLAMA_MODELS:-$MODELS_DEFAULT}"
INIT_MODE="${OLLAMA_INIT_MODE:-pull_missing}"
PULL_OPTIONS="${OLLAMA_PULL_OPTIONS:-}"
RUN_OPTIONS="${OLLAMA_RUN_OPTIONS:-}"
RUN_PROMPT="${OLLAMA_RUN_PROMPT:-Say hello.}"
RETRY_MAX_ATTEMPTS="${OLLAMA_RETRY_MAX_ATTEMPTS:-0}"

echo "Using OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}"
echo "Init mode: ${INIT_MODE}"
echo "Models: ${MODELS}"

run_with_retry() {
  model="$1"
  cmd="$2"
  attempts=0

  until sh -c "$cmd"; do
    attempts=$((attempts + 1))
    if [ "${RETRY_MAX_ATTEMPTS}" -gt 0 ] && [ "${attempts}" -ge "${RETRY_MAX_ATTEMPTS}" ]; then
      echo "Model init failed for ${model} after ${attempts} attempts."
      return 1
    fi
    echo "Retrying ${model} in 3s ..."
    sleep 3
  done
}

model_exists_locally() {
  model="$1"
  ollama show "${model}" >/dev/null 2>&1
}

for model in ${MODELS}; do
  case "${INIT_MODE}" in
    pull)
      echo "Pulling ${model} ..."
      run_with_retry "${model}" "ollama pull ${PULL_OPTIONS} \"${model}\""
      ;;
    pull_missing|pull-missing|pull_if_missing)
      if model_exists_locally "${model}"; then
        echo "Model ${model} already exists locally. Skipping pull."
      else
        echo "Model ${model} is missing locally. Pulling ..."
        run_with_retry "${model}" "ollama pull ${PULL_OPTIONS} \"${model}\""
      fi
      ;;
    run)
      echo "Running ${model} ..."
      run_with_retry "${model}" "ollama run ${RUN_OPTIONS} \"${model}\" \"${RUN_PROMPT}\""
      ;;
    none)
      echo "Skipping model init for ${model} (OLLAMA_INIT_MODE=none)."
      ;;
    *)
      echo "Invalid OLLAMA_INIT_MODE=${INIT_MODE}. Allowed values: pull, pull_missing, run, none."
      exit 1
      ;;
  esac
done

echo "Model init finished successfully."
