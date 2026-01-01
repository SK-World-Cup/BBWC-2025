import os
from threading import Thread
from time import sleep
import requests

from flask import Flask
from bot import bot  # your Discord bot from bot.py

# -------------------- Flask Web Server --------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

def run_webserver():
    # Use Render's PORT env var or fallback to 10000 locally
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)

Thread(target=run_webserver, daemon=True).start()

# Optional: self-ping to stay awake (if needed)
def keep_alive():
    url = os.environ.get("WEB_URL")  # e.g., your Render service URL
    if not url:
        return
    while True:
        try:
            requests.get(url)
        except:
            pass
        sleep(240)

Thread(target=keep_alive, daemon=True).start()

# -------------------- Run Discord Bot --------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set!")

bot.run(TOKEN)


