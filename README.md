# NYX Trading Bot

**Author:** BLESSING OMOREGIE  
**GitHub:** Nixiestone  
**Repository:** nyx_trial

Advanced algorithmic trading bot using Smart Money Concepts (SMC), Machine Learning, and Sentiment Analysis.

## Features

- **Smart Money Concepts (SMC) Strategy**
  - Market Structure Shift (MSS) detection
  - Break of Structure (BOS) identification
  - Order Blocks, Breaker Blocks, Fair Value Gaps
  - POI (Point of Interest) selection
  - Inducement detection

- **Machine Learning Ensemble**
  - Random Forest Classifier
  - Gradient Boosting (XGBoost)
  - LSTM Neural Network
  - Ensemble voting system

- **Sentiment Analysis**
  - Multi-source news aggregation
  - NLP-based sentiment scoring
  - Time-weighted analysis

- **Risk Management**
  - Dynamic position sizing
  - Daily loss limits
  - Maximum position controls
  - Real-time risk monitoring

- **Notifications**
  - Telegram alerts
  - Discord webhooks
  - Email notifications (optional)

## Installation

### Prerequisites

- Python 3.10 or 3.11
- MetaTrader 5 terminal
- MT5 trading account

### Step 1: Clone Repository
```bash
git clone https://github.com/Nixiestone/nyx_trial.git
cd nyx_trial
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure

1. Copy `config/secrets.env.template` to `config/secrets.env`
2. Fill in your credentials:
   - MT5 login, password, server
   - Telegram bot token and chat ID
   - News API key

### Step 5: Test Connection
```bash
python test_mt5_connection.py
```

## Configuration

Edit `config/secrets.env`:
```bash
# MT5 Credentials
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_server

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# News API
NEWS_API_KEY=your_newsapi_key

# Trading
AUTO_TRADING_ENABLED=false  # Set true when ready
```

## Usage

### Run the Bot
```bash
python main.py
```

### Test Individual Components
```bash
# Test MT5 connection
python test_mt5_connection.py

# Test strategy
pytest tests/test_strategy.py

# Test notifications
python -c "from src.notifications.notifier import Notifier; from config.settings import settings; Notifier(settings).test_notifications()"
```

## Project Structure
nyx_trial/
├── config/
│   ├── settings.py          # Configuration
│   └── secrets.env          # Credentials (not in git)
├── src/
│   ├── data/
│   │   ├── mt5_connector.py
│   │   └── news_scraper.py
│   ├── models/
│   │   ├── random_forest_model.py
│   │   ├── gradient_boosting_model.py
│   │   ├── lstm_model.py
│   │   └── ml_ensemble.py
│   ├── strategy/
│   │   ├── structure.py
│   │   ├── poi_detector.py
│   │   └── smc_analysis.py
│   ├── sentiment/
│   │   └── analyzer.py
│   ├── trading/
│   │   ├── mt5_executor.py
│   │   ├── signal_generator.py
│   │   └── risk_manager.py
│   ├── notifications/
│   │   └── notifier.py
│   └── utils/
│       ├── logger.py
│       └── validators.py
├── tests/
├── main.py                  # Main bot
└── requirements.txt

## Trading Strategy

The bot uses a multi-phase SMC strategy:

1. **Phase 1 (HTF):** Identify trend and context
2. **Phase 2 (ITF):** Detect setup (MSS or BOS)
3. **Phase 3 (LTF):** Confirm entry and inducement
4. **Phase 4:** Execute with risk management

## Safety Features

- Testnet mode by default
- Daily loss limits
- Position size limits
- Multi-factor signal validation
- Real-time notifications

## Deployment

### Docker Deployment
```bash
docker-compose up -d
```

### Manual Deployment

See deployment guides in `/docs`

## Troubleshooting

### MT5 Won't Connect

1. Ensure MT5 is running
2. Verify credentials
3. Check server name
4. Try manual login first

### No Signals Generated

This is normal - the strategy is strict and only generates high-quality setups.

### Import Errors
```bash
pip install -r requirements.txt --upgrade
```

## Disclaimer

**IMPORTANT:** This bot is for educational purposes. Trading carries risk. Always:

- Start with demo account
- Test thoroughly
- Use proper risk management
- Never trade with money you can't afford to lose

## License

MIT License - See LICENSE file

## Support

For issues, open a GitHub issue or contact via Telegram.

## Credits

Developed by BLESSING OMOREGIE (Nixiestone)

Based on Smart Money Concepts and modern ML techniques.