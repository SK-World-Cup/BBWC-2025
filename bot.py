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
async def player(ctx, *, player_name: str):
    """Show a player's key stats from the 'Players' sheet."""
    try:
        ws = sheet.worksheet("PLAYERS")
        data = ws.get_all_records()

        # Case-insensitive search
        player = next(
            (p for p in data if p["Player"].strip().lower() == player_name.lower()), None
        )

        if player:
            embed = discord.Embed(
                title=f"🏒 {player['Player']}",
                description=f"Team: **{player.get('Team', 'N/A')}**",
                color=discord.Color.blue()
            )

            # Focused set of meaningful stats
            stats = {
                "Games Played": player.get('Games Played', '—'),
                "Wins": player.get('Wins', '—'),
                "Draws": player.get('Draws', '—'),
                "Losses": player.get('Losses', '—'),
                "Goals": player.get('Goals', '—'),
                "Assists": player.get('Assists', '—'),
                "Clean Sheets": player.get('Clean Sheets', '—'),
                "Goal Diff.": player.get('Goal Diff.', '—'),
                "Goals/Game": player.get('Goals/Game', '—'),
                "Assists/Game": player.get('Assists/Game', '—')
            }

            for stat, value in stats.items():
                embed.add_field(name=stat, value=value if value != "" else "—", inline=True)

            await ctx.send(embed=embed)

        else:
            await ctx.send(f"❌ Player **{player_name}** not found in the sheet.")

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
