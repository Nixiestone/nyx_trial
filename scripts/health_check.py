"""
Production Health Monitoring System
Monitors bot health and sends alerts to admin

Author: BLESSING OMOREGIE
"""

import sys
from pathlib import Path
import asyncio
from datetime import datetime
import psutil

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.database.models import User, MT5Account, Trade, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Bot


class HealthChecker:
    """Monitors bot health and alerts admin."""
    
    def __init__(self):
        self.admin_chat_id = int(settings.TELEGRAM_CHAT_ID) if settings.TELEGRAM_CHAT_ID else None
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else None
        
        # Database
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        self.db = Session()
    
    async def check_health(self) -> dict:
        """Perform comprehensive health check."""
        
        health_report = {
            'timestamp': datetime.utcnow(),
            'status': 'HEALTHY',
            'checks': {}
        }
        
        # 1. Database Health
        try:
            self.db.query(User).first()
            health_report['checks']['database'] = 'OK'
        except Exception as e:
            health_report['checks']['database'] = f'FAIL: {str(e)[:100]}'
            health_report['status'] = 'CRITICAL'
        
        # 2. MT5 Connection
        try:
            from src.data.mt5_connector import MT5Connector
            connector = MT5Connector(settings)
            if connector.connect():
                health_report['checks']['mt5_connection'] = 'OK'
                connector.disconnect()
            else:
                health_report['checks']['mt5_connection'] = 'FAIL: Cannot connect'
                health_report['status'] = 'WARNING'
        except Exception as e:
            health_report['checks']['mt5_connection'] = f'FAIL: {str(e)[:100]}'
            health_report['status'] = 'WARNING'
        
        # 3. System Resources
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            health_report['checks']['cpu'] = f'{cpu_percent}%'
            health_report['checks']['memory'] = f'{memory_percent}%'
            health_report['checks']['disk'] = f'{disk_percent}%'
            
            if cpu_percent > 90 or memory_percent > 90:
                health_report['status'] = 'WARNING'
        except Exception as e:
            health_report['checks']['system_resources'] = f'FAIL: {str(e)[:100]}'
        
        # 4. Active Accounts
        try:
            active_accounts = self.db.query(MT5Account).filter_by(
                status='active',
                auto_trade_enabled=True
            ).count()
            health_report['checks']['active_accounts'] = active_accounts
        except Exception as e:
            health_report['checks']['active_accounts'] = f'FAIL: {str(e)[:100]}'
        
        # 5. Recent Errors
        try:
            error_accounts = self.db.query(MT5Account).filter_by(
                status='error'
            ).count()
            health_report['checks']['error_accounts'] = error_accounts
            
            if error_accounts > 0:
                health_report['status'] = 'WARNING'
        except:
            pass
        
        return health_report
    
    async def send_health_alert(self, health_report: dict):
        """Send health report to admin."""
        
        if not self.admin_chat_id or not self.bot:
            print("Admin notifications not configured")
            return
        
        status_emoji = {
            'HEALTHY': 'OK',
            'WARNING': 'WARNING',
            'CRITICAL': 'CRITICAL'
        }
        
        message = f"""
BOT HEALTH CHECK - {status_emoji.get(health_report['status'], 'UNKNOWN')}

Timestamp: {health_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}
Overall Status: {health_report['status']}

CHECKS:
"""
        
        for check_name, check_result in health_report['checks'].items():
            message += f"  {check_name}: {check_result}\n"
        
        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message.strip()
            )
            print("Health alert sent to admin")
        except Exception as e:
            print(f"Failed to send health alert: {e}")
    
    async def run_continuous_monitoring(self, interval_minutes: int = 30):
        """Run continuous health monitoring."""
        
        print(f"Starting health monitoring (interval: {interval_minutes} minutes)")
        
        while True:
            try:
                health_report = await self.check_health()
                
                print(f"\nHealth Check: {health_report['status']}")
                for check, result in health_report['checks'].items():
                    print(f"  {check}: {result}")
                
                # Send alert if not healthy
                if health_report['status'] != 'HEALTHY':
                    await self.send_health_alert(health_report)
                
                # Wait for next check
                await asyncio.sleep(interval_minutes * 60)
                
            except Exception as e:
                print(f"Health check error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error


async def main():
    """Run health checker."""
    checker = HealthChecker()
    
    # Run initial check
    print("Running initial health check...")
    health_report = await checker.check_health()
    
    print("\nHEALTH CHECK RESULTS:")
    print(f"Status: {health_report['status']}")
    for check, result in health_report['checks'].items():
        print(f"  {check}: {result}")
    
    # Send initial report
    await checker.send_health_alert(health_report)
    
    # Start continuous monitoring
    await checker.run_continuous_monitoring(interval_minutes=30)


if __name__ == "__main__":
    asyncio.run(main())