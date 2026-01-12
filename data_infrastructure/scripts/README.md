
# Vault + IPFS Backup

This setup backs up the only critical data in the system:

- Vault data (Docker volume)
- Vault configuration (host directory)
- IPFS node data (host directory)

It does NOT back up:

- The operating system
- Docker containers or images
- Logs or runtime files

---

## Files

- backup_vault_ipfs.sh   → Backup script
- .env                  → Your local configuration
- .env.example          → Template for .env

---

## Setup

1. Create your config:

   cp .env.example .env
2. Edit `.env` and verify the paths.
3. Make the script executable:

   chmod +x backup_vault_ipfs.sh

---

## Run a Backup

   ./backup_vault_ipfs.sh

The script will:

1. Export the Vault Docker volume
2. Archive the Vault config directory
3. Archive the IPFS repo
4. Encrypt all archives with GPG

Encrypted files are stored locally in:

   BACKUP_DIR/`<hostname>`/`<timestamp>`/

You then upload these `.gpg` files to SharePoint.

---

## Restore

When restoring on a new or repaired machine:

1. You download the `.gpg` files from SharePoint
2. You decrypt them:

   gpg file.tar.gz.gpg
3. You restore the data:

   - Vault volume → extracted back into Docker volume
   - Vault config → extracted to its original path
   - IPFS repo → extracted to ~/.ipfs
4. You start Vault and IPFS again.

Result:

- Vault has all secrets and data
- IPFS keeps the same node identity and pinned content
- The application works exactly as before
