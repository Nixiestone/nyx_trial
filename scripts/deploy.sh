: '
#!/bin/bash
# deploy.sh - Deployment Script for NYX Trading Bot
# Author: BLESSING OMOREGIE
# Location: scripts/deploy.sh

echo "========================================"
echo "NYX TRADING BOT - DEPLOYMENT SCRIPT"
echo "========================================"

# Configuration
ENV=${1:-production}

echo ""
echo "Environment: ${ENV}"
echo ""

# Step 1: Backup current installation
echo "[1/7] Creating backup of current installation..."
bash scripts/backup.sh

# Step 2: Pull latest code
echo "[2/7] Pulling latest code..."
git pull origin main

# Step 3: Update dependencies
echo "[3/7] Updating dependencies..."
pip install -r requirements.txt --upgrade

# Step 4: Run database migrations
echo "[4/7] Running database migrations..."
python scripts/init_database.py

# Step 5: Run tests
echo "[5/7] Running tests..."
python scripts/run_tests.py

# Step 6: Validate configuration
echo "[6/7] Validating configuration..."
python -c "from config.settings import validate_settings; validate_settings()"

# Step 7: Restart service
echo "[7/7] Restarting service..."
if [ -f "nyx_bot.pid" ]; then
    PID=$(cat nyx_bot.pid)
    kill -15 $PID
    echo "Stopped old process (PID: $PID)"
fi

# Start new process
nohup python main.py > logs/bot.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > nyx_bot.pid

echo ""
echo "========================================"
echo "DEPLOYMENT COMPLETE!"
echo "========================================"
echo "New PID: $NEW_PID"
echo "Log file: logs/bot.log"
echo ""
echo "To check status:"
echo "  tail -f logs/bot.log"
echo "========================================"
'