import os
import json
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import gspread
from google.oauth2.service_account import Credentials

# -------------------- Flask Webserver --------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

def run_webserver():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread so Discord bot can run concurrently
Thread(target=run_webserver).start()

# -------------------- Google Sheets Setup --------------------
# GOOGLE_CREDS_JSON should be set as a Render environment variable
creds_json = os.environ.get("GOOGLE_CREDS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDS_JSON environment variable not set!")

# Write credentials to a temporary file
with open("credentials.json", "w") as f:
    f.write(creds_json)

scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
gc = gspread.authorize(creds)

# Example: open a sheet by key
SHEET_ID = os.environ.get("SHEET_ID")  # Set this as a Render env variable
if SHEET_ID:
    try:
        sheet = gc.open_by_key(SHEET_ID)
    except gspread.exceptions.APIError as e:
        print(f"Error accessing sheet: {e}")
else:
    print("No SHEET_ID provided. Google Sheets functions will not work.")

# -------------------- Discord Bot Setup --------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# Only enable basic intents, no privileged ones
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

bot = commands.Bot(command_prefix="!", intents=intents)

# Ping command
@bot.command()
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency: {latency_ms}ms")

# You can add more commands here that interact with Google Sheets
@bot.command(name="player")
async def player(ctx, *, name: str):
    try:
        ws = sheet.worksheet("PLAYERS")
        data = ws.get_all_values()

        # Extract header and rows
        header = data[0]
        rows = data[1:]

        # Find the player's row (case-insensitive match)
        player_row = next((r for r in rows if r[2].strip().lower() == name.lower()), None)

        if not player_row:
            await ctx.send(f"❌ Player '{name}' not found.")
            return

        # Build stats message (adjusted to your column order)
        msg = (
            f"**{player_row[2]}** ({player_row[4]})\n"
            f"Games: {player_row[5]} | Wins: {player_row[6]} | Draws: {player_row[7]} | Losses: {player_row[8]}\n"
            f"Goals: {player_row[9]} | Assists: {player_row[10]}\n"
            f"Goals For: {player_row[11]} | Goals Against: {player_row[12]} | Clean Sheets: {player_row[13]}\n"
            f"Goal Diff: {player_row[14]}\n"
            f"G/Game: {player_row[18]} | A/Game: {player_row[19]}"
        )

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching player data: {e}")


# Example: read first cell
@bot.command()
async def read_sheet(ctx):
    if not SHEET_ID:
        await ctx.send("No sheet configured!")
        return
    try:
        value = sheet.sheet1.cell(1,1).value
        await ctx.send(f"First cell value: {value}")
    except Exception as e:
        await ctx.send(f"Error reading sheet: {e}")

# -------------------- Run Bot --------------------
bot.run(TOKEN)
