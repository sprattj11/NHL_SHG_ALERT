import os
import time
import requests
import socket
import threading
import json
from datetime import datetime


# --- CONFIGURATION ---
SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")
BASE_URL = "https://api.sportradar.us/nhl/trial/v7/en"

PUSHOVER_USER1 = os.getenv("PUSHOVER_USER1")
PUSHOVER_USER2 = os.getenv("PUSHOVER_USER2")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")

CHECK_INTERVAL = 60
PER_GAME_DELAY = 10

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds"

SHG_STATS_FILE = "shg_stats.json"

push_users = [os.getenv("PUSHOVER_USER1"), os.getenv("PUSHOVER_USER2")]


# --- LOCAL SHG RECORD TRACKING ---
def load_shg_stats():
    if os.path.exists(SHG_STATS_FILE):
        try:
            with open(SHG_STATS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_shg_stats(stats):
    with open(SHG_STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def update_team_shg_record(team_id, team_name):
    stats = load_shg_stats()
    if team_id not in stats:
        stats[team_id] = {
            "team_name": team_name,
            "games_with_shg": 0,
            "wins_after_shg": 0,
            "losses_after_shg": 0,
        }

    stats[team_id]["games_with_shg"] += 1
    save_shg_stats(stats)


def record_shg_game_result(winning_team_id, losing_team_id):
    """Increment SHG win/loss totals if teams appear in stats."""
    stats = load_shg_stats()
    if winning_team_id in stats:
        stats[winning_team_id]["wins_after_shg"] += 1
    if losing_team_id in stats:
        stats[losing_team_id]["losses_after_shg"] += 1
    save_shg_stats(stats)


def get_team_shg_record(team_id):
    stats = load_shg_stats()
    team = stats.get(team_id)
    if not team:
        return None
    wins = team["wins_after_shg"]
    losses = team["losses_after_shg"]
    return f"{wins}-{losses} (SHG record)"


# --- PUSHOVER NOTIFICATION ---
def send_notification(team, description):
    odds = None
    if ODDS_API_KEY:
        odds = fetch_odds_for_game(team)
    message = f"Short-handed goal by {team}: {description}"
    if odds:
        ml = odds.get("ml")
        pl = odds.get("puckline")
        extras = []
        if ml is not None:
            extras.append(f"ML: {ml}")
        if pl is not None:
            extras.append(f"Puckline: {pl}")
        if extras:
            message += " | " + " | ".join(extras)

    url = "https://api.pushover.net/1/messages.json"
    for user_key in push_users:
        if not user_key:
            continue  # Skip if env variable not set
        payload = {
            "token": PUSHOVER_TOKEN,
            "user": user_key,
            "title": "NHL SHG Alert",
            "message": message,
        }
        try:
            r = requests.post(url, data=payload)  # <-- move inside the loop
            r.raise_for_status()
            print(f"✅ Notification sent to {user_key}: {message}")
        except Exception as e:
            print(f"❌ Failed to send notification to {user_key}: {e}")


# --- ODDS FETCHING ---
def fetch_odds_for_game(team_name):
    params = {
        "regions": "us",
        "markets": "h2h,spreads",
        "oddsFormat": "american",
        "apiKey": ODDS_API_KEY,
    }
    try:
        resp = requests.get(ODDS_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Failed to fetch odds: {e}")
        return None

    for game in data:
        if team_name == game.get("home_team") or team_name == game.get("away_team"):
            for book in game.get("bookmakers", []):
                ml = None
                pl = None
                for market in book.get("markets", []):
                    if market.get("key") == "h2h":
                        for o in market.get("outcomes", []):
                            if o.get("name") == team_name:
                                ml = o.get("price")
                    if market.get("key") == "spreads":
                        for o in market.get("outcomes", []):
                            if o.get("name") == team_name:
                                pl = f"{o.get('point')} ({o.get('price')})"
                return {"ml": ml, "puckline": pl}
    return None


# --- SPORTRADAR HELPERS ---
def get_today_games():
    today = datetime.now()
    url = f"{BASE_URL}/games/{today.year}/{today.month:02}/{today.day:02}/schedule.json?api_key={SPORTRADAR_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("games", [])
    except Exception as e:
        print(f"❌ Failed to fetch today's games: {e}")
        return []


def get_live_plays(game_id):
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


def get_final_game_result(game_id):
    """Return (winner_id, loser_id) if final."""
    url = f"{BASE_URL}/games/{game_id}/summary.json?api_key={SPORTRADAR_API_KEY}"
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "closed":
            return None, None

        home = data.get("home")
        away = data.get("away")
        if not home or not away:
            return None, None

        if home["points"] > away["points"]:
            return home["id"], away["id"]
        elif away["points"] > home["points"]:
            return away["id"], home["id"]
    except Exception as e:
        print(f"⚠️ Could not fetch final result for {game_id}: {e}")
    return None, None


# --- SHG CHECK ---
def check_shg(plays_seen):
    games = get_today_games()

    for g in games:
        gid = g["id"]
        periods = get_live_plays(gid)
        for p in periods:
            period_num = p.get("number", 0)
            for event in p.get("events", []):
                if (
                    event.get("event_type") == "goal"
                    and event.get("strength") == "shorthanded"
                ):
                    key = f"{gid}-{event['id']}"
                    if key not in plays_seen:
                        team_name = event.get("attribution", {}).get(
                            "name", "Unknown team"
                        )
                        team_id = event.get("attribution", {}).get("id")

                        # Include time left in the period
                        period_time = event.get("clock", "Unknown")
                        desc = event.get("description", "No description")
                        desc += f" | Period {period_num} - Time left: {period_time}"

                        # Update SHG stats
                        update_team_shg_record(team_id, team_name)
                        shg_record = get_team_shg_record(team_id)
                        if shg_record:
                            desc += f" | Team record: {shg_record}"

                        # Send notification
                        send_notification(team_name, desc)
                        plays_seen.add(key)

        time.sleep(PER_GAME_DELAY)

    # After scanning live games, check finals
    for g in games:
        gid = g["id"]
        if g.get("status") == "closed":
            winner, loser = get_final_game_result(gid)
            if winner and loser:
                record_shg_game_result(winner, loser)


# --- DUMMY TEST MODE ---
def test_mode():
    print("Running dummy test (sending real Pushover notification)...")
    fake_goal = {
        "event_type": "goal",
        "strength": "shorthanded",
        "description": "Connor McDavid scores short-handed breakaway goal!",
        "attribution": {
            "name": "Test Team",
            "id": "44174b0d-0f24-11e2-8525-18a905767e44",
        },
    }

    update_team_shg_record(
        fake_goal["attribution"]["id"], fake_goal["attribution"]["name"]
    )
    shg_record = get_team_shg_record(fake_goal["attribution"]["id"])
    desc = f"{fake_goal['description']} | Team record: {shg_record} | Period 2 - Time left: 05:32"
    send_notification(fake_goal["attribution"]["name"], desc)
    print("✅ Dummy alert sent to your Pushover app")


# --- DUMMY SERVER (for Render) ---
def start_dummy_server():
    port = int(os.environ.get("PORT", "10000"))
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


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        main(test=True)
    else:
        main()
