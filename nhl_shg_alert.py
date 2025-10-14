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

CHECK_INTERVAL = 60  # seconds between full live checks
PER_GAME_DELAY = 10  # seconds between each game's API call


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
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"⚠️ 429 Rate Limit hit for game {game_id}, pausing 30s...")
            time.sleep(30)
            return []
        raise
    except Exception as e:
        print(f"❌ Failed to fetch live plays for game {game_id}: {e}")
        return []


# --- CHECK SHORT-HANDED GOALS ---
def check_shg(plays_seen):
    """Check all live games for new short-handed goals and send real notifications."""
    game_ids = get_today_games()

    for gid in game_ids:
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

        # Delay between per-game API calls to avoid rate limits
        time.sleep(PER_GAME_DELAY)


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


# --- DUMMY SERVER (for Render) ---
def start_dummy_server():
    port = int(os.environ.get("PORT", "10000"))  # Render sets PORT for web services
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(1)
    while True:
        conn, _ = s.accept()
        conn.close()


threading.Thread(target=start_dummy_server, daemon=True).start()


# --- MAIN LOOP ---
def main(test=False):
    if test:
        test_mode()
        return

    plays_seen = set()
    print("🚨 Starting NHL short-handed goal alert service (Sportradar API)...\n")
    try:
        while True:
            check_shg(plays_seen)
            print("✅ Completed one full scan — sleeping 60s...\n")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Short-Handed Goal Alert system. Goodbye!\n")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        time.sleep(30)


# --- ENTRY POINT ---
if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        main(test=True)
    else:
        main()