#!/bin/sh
set -eu

CERT_DIR="${CERT_DIR:-/certs}"
CERT_FILE="${CERT_FILE:-${CERT_DIR}/cert.pem}"
KEY_FILE="${KEY_FILE:-${CERT_DIR}/key.pem}"
CAROOT_DIR="${CAROOT_DIR:-${CERT_DIR}/.caroot}"
MKCERT_BIN="/go/bin/mkcert"

if [ -s "${CERT_FILE}" ] && [ -s "${KEY_FILE}" ]; then
  echo "TLS certs already present at ${CERT_DIR}, skipping generation."
  exit 0
fi

echo "Generating local TLS certs via mkcert (containerized)..."
mkdir -p "${CERT_DIR}" "${CAROOT_DIR}"

if [ -s "${CAROOT_DIR}/rootCA.pem" ] && [ ! -s "${CAROOT_DIR}/rootCA-key.pem" ]; then
  echo "Detected inconsistent CA state in ${CAROOT_DIR} (missing rootCA-key.pem), resetting local CA files."
  rm -f "${CAROOT_DIR}/rootCA.pem" "${CERT_FILE}" "${KEY_FILE}"
fi

apk add --no-cache ca-certificates >/dev/null
go install filippo.io/mkcert@latest

CAROOT="${CAROOT_DIR}" "${MKCERT_BIN}" \
  -cert-file "${CERT_FILE}" \
  -key-file "${KEY_FILE}" \
  localhost 127.0.0.1 ::1

echo "Generated ${CERT_FILE} and ${KEY_FILE}."
