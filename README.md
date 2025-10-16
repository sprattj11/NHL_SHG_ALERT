# NHL Short-Handed Goal Alert  
### Jason Spratt — October 2025  

This Python script sends live notifications for NHL short-handed goals using the Sportradar API and Pushover.  
It can run 24/7 on Render.com or locally on your machine.

------------------------------------------------------------
🚀 FEATURES
------------------------------------------------------------
- Polls live NHL games for short-handed goals in real time
- Sends instant push notifications via Pushover
- Dummy test mode for verifying notifications
- Graceful shutdown handling (Ctrl +C)
- Rate-limit aware polling (safe for free Sportradar tier)
- Headless operation (no web interface needed)
- Runtime JSON stats handled safely (won’t conflict with Git)

------------------------------------------------------------
🧰 REQUIREMENTS
------------------------------------------------------------
- Python 3.8+
- requests library (pip install requests)
- Pushover account (https://pushover.net)
  - You’ll need both a User Key and an App Token
- Sportradar NHL API key (https://developer.sportradar.com)
- The Odds API key (https://the-odds-api.com/)

------------------------------------------------------------
⚙️ INSTALLATION
------------------------------------------------------------
1. Clone the repository:
   git clone https://github.com/<your-username>/nhl_shg_alert.git
   cd nhl_shg_alert

2. (Optional) Create and activate a virtual environment:
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate   # Windows

3. Install dependencies:
   pip install requests

4. Set environment variables:

   macOS/Linux:
     export SPORTRADAR_API_KEY="your_sportradar_api_key"
     export PUSHOVER_USER="your_pushover_user_key"
     export PUSHOVER_TOKEN="your_pushover_app_token"
     export ODDS_API_KEY="your_the_odds_api_key"

   Windows (PowerShell):
     setx SPORTRADAR_API_KEY "your_sportradar_api_key"
     setx PUSHOVER_USER "your_pushover_user_key"
     setx PUSHOVER_TOKEN "your_pushover_app_token"
     setx ODDS_API_KEY="your_the_odds_api_key"

------------------------------------------------------------
▶️ USAGE
------------------------------------------------------------
Dummy test (sends real Pushover notification):
   python3 nhl_shg_alert.py --test

Start the live alert service:
   python3 nhl_shg_alert.py

Press Ctrl +C to stop the service.

------------------------------------------------------------
☁️ DEPLOYING ON RENDER
------------------------------------------------------------
1. Push your repository to GitHub.
2. Go to https://render.com and create a new Web Service.
3. Connect your GitHub repo.
4. Set Environment Variables:
   - SPORTRADAR_API_KEY
   - PUSHOVER_USER
   - PUSHOVER_TOKEN
   - ODDS_API_KEY
5. Start command:
   python3 nhl_shg_alert.py
6. If you see 'No open ports detected' — that's normal. The dummy server keeps it alive.

------------------------------------------------------------
🧩 DATA FLOW
------------------------------------------------------------
NHL API → nhl_shg_alert.py → Pushover → Your Phone

------------------------------------------------------------
🪶 EXAMPLE NOTIFICATION
------------------------------------------------------------
NHL SHG Alert
Short-handed goal by Edmonton Oilers: Connor McDavid scores short-handed breakaway goal! | Team record: 1-0 (SHG Record) | ML: -170 | Puckline: -1.5 (145) | Period: 2 - Time Left: 05:32

------------------------------------------------------------
🧹 GRACEFUL EXIT
------------------------------------------------------------
When stopped with Ctrl +C, the script logs:
🛑 Shutting down Short-Handed Goal Alert system. Goodbye!

------------------------------------------------------------
📄 LICENSE
------------------------------------------------------------
MIT License — feel free to modify and extend for your own projects.

------------------------------------------------------------
👨‍💻 AUTHOR
------------------------------------------------------------
Jason Spratt  
Built in Python — October 2025
