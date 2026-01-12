#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------
# Backup Vault (Docker volume) + Vault config (host) + IPFS repo (host)
# Produces encrypted .tar.gz.gpg files locally.
# Upload to SharePoint is NOT done here (you upload manually).
# ---------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"

# Load .env
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env file not found at: $ENV_FILE" >&2
  exit 1
fi

# Export variables declared in .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# Defaults (can be overridden by .env)
VAULT_VOLUME="${VAULT_VOLUME:-data_infrastructure_vault_data}"
VAULT_CONFIG_DIR="${VAULT_CONFIG_DIR:-}"
IPFS_DIR="${IPFS_DIR:-${IPFS_PATH:-$HOME/.ipfs}}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"
KEEP_PLAINTEXT_TARS="${KEEP_PLAINTEXT_TARS:-0}"   # 1 = keep .tar.gz, 0 = delete after encrypting

DATE_STR="$(date +%F_%H-%M-%S)"
HOST="$(hostname -s 2>/dev/null || echo host)"
OUT_DIR="${BACKUP_DIR}/${HOST}/${DATE_STR}"

mkdir -p "$OUT_DIR"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

echo "== Checking tools =="
require_cmd tar
require_cmd gpg
require_cmd docker

echo "== Sanity checks =="
if ! docker volume inspect "$VAULT_VOLUME" >/dev/null 2>&1; then
  echo "ERROR: Docker volume not found: $VAULT_VOLUME" >&2
  exit 1
fi

if [[ -z "${VAULT_CONFIG_DIR}" ]]; then
  echo "ERROR: VAULT_CONFIG_DIR is empty. Set it in .env." >&2
  exit 1
fi
if [[ ! -d "$VAULT_CONFIG_DIR" ]]; then
  echo "ERROR: VAULT_CONFIG_DIR not found: $VAULT_CONFIG_DIR" >&2
  exit 1
fi

if [[ ! -d "$IPFS_DIR" ]]; then
  echo "ERROR: IPFS_DIR not found: $IPFS_DIR" >&2
  exit 1
fi

echo "== Output directory: $OUT_DIR =="

backup_vault_volume() {
  local out_tar="${OUT_DIR}/vault_data_${VAULT_VOLUME}_${DATE_STR}.tar.gz"
  echo "== Backing up Vault volume ($VAULT_VOLUME) -> $(basename "$out_tar") =="

  docker run --rm \
    -v "${VAULT_VOLUME}:/data:ro" \
    -v "${OUT_DIR}:/backup" \
    alpine sh -c "cd /data && tar -czf /backup/$(basename "$out_tar") ."
}

backup_vault_config() {
  local out_tar="${OUT_DIR}/vault_config_${DATE_STR}.tar.gz"
  echo "== Backing up Vault config ($VAULT_CONFIG_DIR) -> $(basename "$out_tar") =="

  # Store the directory with its full path for simple restore to /
  tar -czf "$out_tar" "$VAULT_CONFIG_DIR"
}

backup_ipfs() {
  local out_tar="${OUT_DIR}/ipfs_${DATE_STR}.tar.gz"
  echo "== Backing up IPFS repo ($IPFS_DIR) -> $(basename "$out_tar") =="

  tar -czf "$out_tar" -C "$(dirname "$IPFS_DIR")" "$(basename "$IPFS_DIR")"
}

encrypt_file() {
  local f="$1"
  echo "== Encrypting $(basename "$f") -> $(basename "$f").gpg =="

  # Symmetric encryption (prompts for passphrase unless you use gpg-agent/pinentry)
  gpg --batch --yes --symmetric --cipher-algo AES256 "$f"

  if [[ "$KEEP_PLAINTEXT_TARS" == "0" ]]; then
    rm -f "$f"
  fi
}

echo "== Starting backup =="
backup_vault_volume
backup_vault_config
backup_ipfs

echo "== Encrypting outputs =="
shopt -s nullglob
for f in "$OUT_DIR"/*.tar.gz; do
  encrypt_file "$f"
done
shopt -u nullglob

echo
echo "== Done. Encrypted backups are here: =="
echo "$OUT_DIR"
ls -lh "$OUT_DIR"

echo
echo "Next: upload the .gpg files in that folder to SharePoint (manual upload)."
