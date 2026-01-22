"""
Production Startup Script with Health Server
Runs both bot and health check server
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment first
import load_environment
load_environment.load_environment()

# Import both services
from main import ProductionTradingBot


async def run_all_services():
    """Run bot and health server concurrently."""
    # Start health server
    health_server = HealthCheckServer(port=8080)
    await health_server.start()
    
    # Start trading bot
    bot = ProductionTradingBot()
    
    # Run both concurrently
    bot_task = asyncio.create_task(bot.run())
    
    # Keep health server running
    await bot_task


if __name__ == "__main__":
    try:
        asyncio.run(run_all_services())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)