# NHL Short-Handed Goal Alert 
# Jason Spratt October 2025

This Python script sends **live notifications** for NHL short-handed goals using the **Sportradar API** and **Pushover**.  

It can run 24/7 on Render.com or any Python environment.

---

## Features

- Polls live NHL games for short-handed goals.
- Sends instant Pushover notifications.
- Dummy test mode for testing notifications.
- Fully configurable via environment variables.
- Runs continuously without a web interface.

---

## Requirements

- Python 3.8+
- `requests` library
- Pushover account (user key + app token)
- Sportradar NHL API key

---

## Installation

1. Clone this repository:

```bash
git clone <YOUR_REPO_URL>
cd nhl_shg_alert