import os
from flask import Flask
from threading import Thread
import requests
from time import sleep, time

app = Flask(__name__)
last_ping = 0

@app.route("/")
def home():
    global last_ping
    if time() - last_ping < 2:
        return "", 429
    last_ping = time()
    return "Bot is alive", 200

def run_webserver():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)

Thread(target=run_webserver).start()

def keep_alive():
    url = os.environ.get("WEB_URL")
    if not url:
        return
    while True:
        try:
            requests.get(url)
        except:
            pass
        sleep(240)

Thread(target=keep_alive, daemon=True).start()

