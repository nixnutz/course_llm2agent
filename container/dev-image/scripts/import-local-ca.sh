#!/bin/sh
set -eu

CA_SOURCE="${DEV_LOCAL_CA_SOURCE:-/certs/.caroot/rootCA.pem}"
CA_TARGET="${DEV_LOCAL_CA_TARGET:-/usr/local/share/ca-certificates/dev-local-root-ca.crt}"

if [ ! -s "${CA_SOURCE}" ]; then
  echo "INFO: local CA not found at ${CA_SOURCE}, skipping trust import."
  exit 0
fi

sudo mkdir -p "$(dirname "${CA_TARGET}")"
sudo cp "${CA_SOURCE}" "${CA_TARGET}"
sudo chmod 0644 "${CA_TARGET}"
sudo update-ca-certificates >/dev/null

echo "Imported local CA into container trust store: ${CA_TARGET}"
