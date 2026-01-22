#!/bin/bash
# backup.sh - Automated Backup Script for NYX Trading Bot
# Author: BLESSING OMOREGIE
# Location: scripts/backup.sh

echo "========================================"
echo "NYX TRADING BOT - BACKUP SCRIPT"
echo "========================================"

# Configuration
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="nyx_backup_${DATE}"

# Create backup directory
mkdir -p ${BACKUP_DIR}

echo ""
echo "[1/5] Creating backup directory..."
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup database
echo "[2/5] Backing up database..."
cp -r data/ "${BACKUP_DIR}/${BACKUP_NAME}/data/"

# Backup configuration (excluding secrets)
echo "[3/5] Backing up configuration..."
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}/config"
cp config/settings.py "${BACKUP_DIR}/${BACKUP_NAME}/config/"
cp config/secrets.env.template "${BACKUP_DIR}/${BACKUP_NAME}/config/"

# Backup logs
echo "[4/5] Backing up logs..."
if [ -d "logs" ]; then
    cp -r logs/ "${BACKUP_DIR}/${BACKUP_NAME}/logs/"
fi

# Backup models
echo "[5/5] Backing up models..."
if [ -d "models" ]; then
    cp -r models/ "${BACKUP_DIR}/${BACKUP_NAME}/models/"
fi

# Create archive
echo ""
echo "Creating compressed archive..."
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C "${BACKUP_DIR}" "${BACKUP_NAME}"

# Remove temporary directory
rm -rf "${BACKUP_DIR}/${BACKUP_NAME}"

# Show result
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
echo ""
echo "========================================"
echo "BACKUP COMPLETE!"
echo "========================================"
echo "File: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo ""
echo "To restore:"
echo "  tar -xzf ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "========================================"