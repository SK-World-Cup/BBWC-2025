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

@bot.command(name="standings")
async def standings(ctx):
    """Shows the top 10 teams in the tournament standings."""
    try:
        sheet_data = sheet.worksheet("GROUP_STAGE")
        all_rows = sheet_data.get_all_values()

        # Headers and actual data (adjusted to your described structure)
        headers = all_rows[6]   # Row 7 in Sheets (0-index)
        data = all_rows[7:17]   # Rows 8–17

        # Find index positions for columns
        team_idx = headers.index("Team")
        gp_idx = headers.index("GP")
        w_idx = headers.index("W")
        d_idx = headers.index("D")
        l_idx = headers.index("L")
        gf_idx = headers.index("GF")
        ga_idx = headers.index("GA")
        gd_idx = headers.index("GD")
        pts_idx = headers.index("PTS")

        # Parse data and sort by PTS descending
        parsed = []
        for row in data:
            try:
                pts = int(row[pts_idx])
            except ValueError:
                pts = 0
            parsed.append({
                "team": row[team_idx],
                "gp": row[gp_idx],
                "w": row[w_idx],
                "d": row[d_idx],
                "l": row[l_idx],
                "gf": row[gf_idx],
                "ga": row[ga_idx],
                "gd": row[gd_idx],
                "pts": pts
            })

        sorted_data = sorted(parsed, key=lambda x: x["pts"], reverse=True)

        # Build leaderboard text
        msg = "**🏆 WORLD CUP 2025 STANDINGS 🏆**\n"
        msg += "```"
        msg += f"{'Rank':<5}{'Team':<18}{'GP':<4}{'W':<4}{'D':<4}{'L':<4}{'GF':<4}{'GA':<4}{'GD':<5}{'PTS':<5}\n"
        msg += "-" * 60 + "\n"
        for i, team in enumerate(sorted_data[:10], start=1):
            msg += f"{i:<5}{team['team'][:16]:<18}{team['gp']:<4}{team['w']:<4}{team['d']:<4}{team['l']:<4}{team['gf']:<4}{team['ga']:<4}{team['gd']:<5}{team['pts']:<5}\n"
        msg += "```"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching standings: {e}")

@bot.command(name="team")
async def team(ctx, *, team_name: str):
    """Shows all players from a team and that team's overall stats."""
    try:
        # Access both sheets
        players_ws = sheet.worksheet("PLAYERS")
        standings_ws = sheet.worksheet("GROUP_STAGE")

        # ---- Get Player List ----
        all_players = players_ws.get_all_values()
        headers = all_players[2]  # row 3 usually headers (adjust if needed)
        team_col = headers.index("Team")
        player_col = headers.index("Player")

        players = [row[player_col] for row in all_players[3:] if len(row) > team_col and row[team_col].strip().lower() == team_name.lower()]

        if not players:
            await ctx.send(f"⚠️ No players found for **{team_name}**.")
            return

        # ---- Get Team Totals ----
        all_rows = standings_ws.get_all_values()
        headers2 = all_rows[6]  # Row 7 = headers
        data = all_rows[7:17]   # Rows 8–17

        team_idx = headers2.index("Team")
        totals = None
        for row in data:
            if len(row) > team_idx and row[team_idx].strip().lower() == team_name.lower():
                totals = {
                    "GP": row[headers2.index("GP")],
                    "W": row[headers2.index("W")],
                    "D": row[headers2.index("D")],
                    "L": row[headers2.index("L")],
                    "GF": row[headers2.index("GF")],
                    "GA": row[headers2.index("GA")],
                    "GD": row[headers2.index("GD")],
                    "PTS": row[headers2.index("PTS")]
                }
                break

        # ---- Build Message ----
        msg = f"**🏒 {team_name.upper()} TEAM SUMMARY 🏒**\n\n"
        msg += "__Players:__\n"
        msg += ", ".join(players) + "\n\n"

        if totals:
            msg += "__Team Totals:__\n"
            msg += f"**GP:** {totals['GP']} | **W:** {totals['W']} | **D:** {totals['D']} | **L:** {totals['L']}\n"
            msg += f"**GF:** {totals['GF']} | **GA:** {totals['GA']} | **GD:** {totals['GD']} | **PTS:** {totals['PTS']}"
        else:
            msg += "_No team totals found in GROUP_STAGE._"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching team info: {e}")



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
