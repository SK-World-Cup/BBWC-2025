# bot.py
import os
import discord
from discord.ext import commands
import gspread
from google.oauth2.service_account import Credentials
from flask import Flask

# ------------------------
# Web server for Render
# ------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

# Detect Render port or default to 5000
port = int(os.environ.get("PORT", 5000))

# ------------------------
# Discord Bot setup
# ------------------------
TOKEN = os.environ.get("DISCORD_TOKEN")  # set this in Render's environment variables
intents = discord.Intents.default()
# Don't enable privileged intents
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------
# Google Sheets setup
# ------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Make sure your credentials file is uploaded as 'credentials.json'
creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
gc = gspread.authorize(creds)

# Example: Open a sheet by key
SHEET_ID = os.environ.get("SHEET_ID")  # store in Render env vars
try:
    sheet = gc.open_by_key(SHEET_ID)
except Exception as e:
    print(f"Error accessing sheet: {e}")
    sheet = None

# ------------------------
# Discord Commands
# ------------------------
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# ------------------------
# Run both Flask and Discord
# ------------------------
def run_flask():
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()

if __name__ == "__main__":
    run_flask()
    bot.run(TOKEN)
