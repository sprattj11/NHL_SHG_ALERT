import os
import time
import requests
import socket
import threading
from datetime import datetime

# --- CONFIGURATION ---
SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")  # Your Sportradar API key
BASE_URL = "https://api.sportradar.us/nhl/trial/v7/en"

PUSHOVER_USER = os.getenv("PUSHOVER_USER")   # Your Pushover user key
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN") # Your Pushover app token

CHECK_INTERVAL = 60  # seconds between live checks

# --- PUSHOVER NOTIFICATION ---
def send_notification(team, description):
    """Send a notification via Pushover."""
    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "title": "NHL SHG Alert",
        "message": f"Short-handed goal by {team}: {description}"
    }
    try:
        r = requests.post(url, data=payload)
        r.raise_for_status()
        print(f"✅ Notification sent for {team}: {description}")
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")

# --- SPORTRADAR API HELPERS ---
def get_today_games():
    """Return a list of game IDs for today."""
    today = datetime.now()
    url = f"{BASE_URL}/games/{today.year}/{today.month:02}/{today.day:02}/schedule.json?api_key={SPORTRADAR_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return [game["id"] for game in data.get("games", []) if game.get("status") in ["inprogress", "scheduled"]]
    except Exception as e:
        print(f"❌ Failed to fetch today's games: {e}")
        return []

def get_live_plays(game_id):
    """Return live play-by-play events for a game."""
    url = f"{BASE_URL}/games/{game_id}/pbp.json?api_key={SPORTRADAR_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("periods", [])
    except Exception as e:
        print(f"❌ Failed to fetch live plays for game {game_id}: {e}")
        return []

# --- CHECK SHORT-HANDED GOALS ---
def check_shg(plays_seen):
    """Check all live games for new short-handed goals and send real notifications."""
    for gid in get_today_games():
        periods = get_live_plays(gid)
        for p in periods:
            for event in p.get("events", []):
                if event.get("event_type") == "goal" and event.get("strength") == "shorthanded":
                    key = f"{gid}-{event['id']}"
                    if key not in plays_seen:
                        desc = event.get("description", "No description")
                        team = event.get("attribution", {}).get("name", "Unknown team")
                        send_notification(team, desc)
                        plays_seen.add(key)

# --- DUMMY TEST MODE ---
def test_mode():
    print("Running dummy test (sending real Pushover notification)...")
    fake_goal = {
        "event_type": "goal",
        "strength": "shorthanded",
        "description": "Connor McDavid scores short-handed breakaway goal!",
        "attribution": {"name": "Edmonton Oilers"}
    }
    send_notification(fake_goal["attribution"]["name"], fake_goal["description"])
    print("✅ Dummy alert sent to your Pushover app")

# Dummy server to satisfy Render
def dummy_server():
    s = socket.socket()
    s.bind(("0.0.0.0", 10000))  # choose any port
    s.listen(1)
    while True:
        conn, addr = s.accept()
        conn.close()

threading.Thread(target=dummy_server, daemon=True).start()

# --- MAIN LOOP ---
def main(test=False):
    if test:
        test_mode()
        return

    plays_seen = set()
    print("Starting NHL short-handed goal alert service (Sportradar API)...")
    while True:
        try:
            check_shg(plays_seen)
        except Exception as e:
            print(f"❌ Error during check: {e}")
        time.sleep(CHECK_INTERVAL)

# --- ENTRY POINT ---
if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        main(test=True)
    else:
        main()