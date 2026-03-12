import os
from threading import Thread
from time import sleep
import requests
import logging

from flask import Flask
from bot import bot  # your Discord bot from bot.py

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- Flask Web Server --------------------
app = Flask(__name__)

@app.route("/")
def home():
    logger.info("Health check ping received")
    return "Bot is alive", 200

@app.route("/health")
def health():
    return "OK", 200

def run_webserver():
    """Run Flask in a separate thread"""
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting web server on port {port}")
    # Use debug=False and don't use reloader to avoid threads issues
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# Start web server in a daemon thread
webserver_thread = Thread(target=run_webserver, daemon=True)
webserver_thread.start()
logger.info("Web server thread started")

# -------------------- Keep Alive (Self-ping) --------------------
def keep_alive():
    """Ping the bot's own URL to keep it awake (for Render free tier)"""
    url = os.environ.get("WEB_URL")
    if not url:
        logger.warning("WEB_URL not set - keep-alive disabled")
        return
    
    logger.info(f"Keep-alive thread started, pinging {url} every 240 seconds")
    
    # Ensure URL has proper format
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    ping_count = 0
    while True:
        try:
            sleep(240)  # Wait 4 minutes between pings
            response = requests.get(url, timeout=30)
            ping_count += 1
            logger.info(f"Keep-alive ping #{ping_count}: Status {response.status_code}")
        except requests.exceptions.Timeout:
            logger.warning(f"Keep-alive ping #{ping_count} timed out")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Keep-alive ping #{ping_count} connection error")
        except Exception as e:
            logger.error(f"Keep-alive ping #{ping_count} failed: {e}")

# Start keep-alive in a daemon thread
keep_alive_thread = Thread(target=keep_alive, daemon=True)
keep_alive_thread.start()
logger.info("Keep-alive thread started")

# -------------------- Run Discord Bot --------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN not set!")

logger.info("Starting Discord bot...")
try:
    bot.run(TOKEN)
except Exception as e:
    logger.error(f"Discord bot crashed: {e}")
    raise
