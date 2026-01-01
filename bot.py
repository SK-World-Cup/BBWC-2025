import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # or DEBUG for more detail
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
import os
import json
import discord
from discord.ext import commands
from threading import Thread
import gspread
from google.oauth2.service_account import Credentials
from time import time, sleep
import requests

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
def get_sheet():
    SHEET_ID = os.environ.get("SHEET_ID")
    if not SHEET_ID:
        raise RuntimeError("SHEET_ID not set")
    return gc.open_by_key(SHEET_ID)

# -------------------- Discord Bot Setup --------------------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set!")

# Only enable basic intents, no privileged ones
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

# ✅ Create the bot object here
bot = commands.Bot(command_prefix="$", intents=intents)

# -------------------- Event Handlers --------------------
@bot.event
async def on_ready():
    logging.info(f"Bot connected as {bot.user}")

@bot.event
async def on_disconnect():
    logging.warning("Bot disconnected from Discord.")

@bot.event
async def on_resumed():
    logging.info("Bot reconnected to Discord.")

@bot.event
async def on_error(event, *args, **kwargs):
    logging.exception(f"Unhandled error in event: {event}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # silently ignore unknown commands
    raise error  # let other errors bubble up



import random

# List of exempt IDs (0% chance of failure)
exempt_ids = [
    1035911200237699072,
    1399947172723818606,
    439236099236429825
]

# Dictionary of custom error messages for specific IDs
custom_errors = {
    444444444444444444: "🚫 Custom Error: You triggered the special block!",
    555555555555555555: "⚡ Custom Error: Access denied for you only!",
    666666666666666666: "🛑 Custom Error: This command is off-limits!"
}

@bot.check
async def global_random_fail(ctx):
    # Exempt users always succeed
    if ctx.author.id in exempt_ids:
        return True

    # 1% chance of error for everyone else
    if random.randint(1, 100) == 1:
        # If the user has a custom error, use it
        if ctx.author.id in custom_errors:
            await ctx.send(custom_errors[ctx.author.id])
        else:
            # Normal error for everyone else
            await ctx.send("❌Error: imagine being unlucky and getting a 1% chance error. From yours truly, Tater.")
        return False  # stops the command
    return True  # allows the command normally





# Ping command
@bot.command(name="ping")
async def ping(ctx):
    """Checks if the bot is online and responsive."""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latency: {latency_ms}ms")

# You can add more commands here that interact with Google Sheets
@bot.command(name="player")
async def player(ctx, *, name: str):
    """Displays stats for a specific player from the PLAYERS sheet."""
    try:
        sheet = get_sheet()
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
    """Shows the tournament standings of every team sorted by points."""
    try:
        sheet = get_sheet()
        sheet_data = sheet.worksheet("GROUP_STAGE")
        all_rows = sheet_data.get_all_values()

        # Headers and actual data (adjusted to your described structure)
        headers = all_rows[6]   # Row 7 in Sheets (0-index)
        data = all_rows[7:16]   # Rows 8–17

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
    """Shows all players from a team with stats and the team's overall totals."""
    try:
        sheet = get_sheet()
        players_ws = sheet.worksheet("PLAYERS")
        standings_ws = sheet.worksheet("GROUP_STAGE")

        # ---- Get Player List ----
        all_players = players_ws.get_all_values()
        headers = [h.strip().lower() for h in all_players[3]]  # row 4

        player_col = headers.index("player")
        team_col = headers.index("team")
        gp_col = headers.index("gp")
        goals_col = headers.index("g")
        assists_col = headers.index("a")

        players_data = []
        for row in all_players[4:]:
            if len(row) > team_col and row[team_col].strip().lower() == team_name.lower():
                player_name = row[player_col]
                gp = row[gp_col] if len(row) > gp_col else "0"
                g = row[goals_col] if len(row) > goals_col else "0"
                a = row[assists_col] if len(row) > assists_col else "0"
                players_data.append(f"{player_name}: {gp} GP | {g} G | {a} A")

        if not players_data:
            await ctx.send(f"⚠️ No players found for **{team_name}**.")
            return

        # ---- Get Team Totals ----
        all_rows = standings_ws.get_all_values()
        headers2 = [h.strip().lower() for h in all_rows[6]]  # row 7
        data = all_rows[7:17]

        team_idx = headers2.index("team")
        totals = None
        for row in data:
            if len(row) > team_idx and row[team_idx].strip().lower() == team_name.lower():
                def get(col):
                    return row[headers2.index(col)] if col in headers2 else "—"

                totals = {
                    "gp": get("gp"),
                    "w": get("w"),
                    "d": get("d"),
                    "l": get("l"),
                    "gf": get("gf"),
                    "ga": get("ga"),
                    "gd": get("gd"),
                    "pts": get("pts"),
                }
                break

        # ---- Build Message ----
        msg = f"**🏒 {team_name.upper()} TEAM SUMMARY 🏒**\n\n"
        msg += "__Players:__\n" + "\n".join(players_data) + "\n\n"

        if totals:
            msg += "__Team Totals:__\n"
            msg += (
                f"**GP:** {totals['gp']} | **W:** {totals['w']} | **D:** {totals['d']} | **L:** {totals['l']}\n"
                f"**GF:** {totals['gf']} | **GA:** {totals['ga']} | **GD:** {totals['gd']} | **PTS:** {totals['pts']}"
            )
        else:
            msg += "_No team totals found in GROUP_STAGE._"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching team info: {e}")

@bot.command(name="topscorers")
async def topscorers(ctx):
    """Shows the top 10 goal scorers from the PLAYERS sheet, with GP as tiebreaker."""
    try:
        sheet = get_sheet()
        ws = sheet.worksheet("PLAYERS")
        all_rows = ws.get_all_values()

        # Headers are on row 4 (index 3), data starts at row 5 (index 4)
        headers = [h.strip().lower() for h in all_rows[3]]
        data = all_rows[4:]

        # Find column indexes
        player_idx = headers.index("player")
        team_idx = headers.index("team")
        gp_idx = headers.index("gp")
        g_idx = headers.index("g")
        a_idx = headers.index("a")

        # Parse players
        parsed = []
        for row in data:
            try:
                goals = int(row[g_idx]) if row[g_idx].isdigit() else 0
            except Exception:
                goals = 0
            try:
                gp = int(row[gp_idx]) if row[gp_idx].isdigit() else 0
            except Exception:
                gp = 0
            assists = row[a_idx] if len(row) > a_idx else "0"

            parsed.append({
                "player": row[player_idx],
                "team": row[team_idx],
                "gp": gp,
                "goals": goals,
                "assists": assists
            })

        # Sort by goals descending, then GP ascending (fewer games = higher rank)
        sorted_players = sorted(parsed, key=lambda x: (-x["goals"], x["gp"]))

        # Build leaderboard text
        msg = "**⚽ TOP 10 GOALSCORERS ⚽**\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(sorted_players[:10], start=1):
            rank = medals[i-1] if i <= 3 else f"{i}."
            msg += f"{rank} {p['player']} ({p['team']}) - {p['goals']} G, {p['assists']} A, {p['gp']} GP\n"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching top scorers: {e}")

from gspread.utils import ValueRenderOption

@bot.command(name="matchlink")
async def matchlink(ctx, team1: str, team2: str):
    """Provides the video link for a match between two teams."""
    try:
        sheet = get_sheet()
        ws = sheet.worksheet("MATCHES")  # adjust to your sheet/tab name
        all_rows = ws.get_all_values()

        # Column indexes (0-based: D=3, F=5, Q=16)
        link_idx = 3
        team_a_idx = 5
        team_b_idx = 16

        found_row = None
        for i, row in enumerate(all_rows[1:], start=2):  # start=2 because Sheets rows are 1-based
            if len(row) > max(link_idx, team_a_idx, team_b_idx):
                t_a = row[team_a_idx].strip().lower()
                t_b = row[team_b_idx].strip().lower()
                if {t_a, t_b} == {team1.lower(), team2.lower()}:
                    found_row = i
                    break

        if found_row:
            # Get the raw formula from column D
            raw = ws.cell(found_row, link_idx + 1,
                          value_render_option=ValueRenderOption.formula).value

            link = None
            if raw and raw.startswith("=HYPERLINK("):
                # Extract URL between the first pair of quotes
                link = raw.split('"')[1]
            else:
                link = ws.cell(found_row, link_idx + 1).value  # fallback to plain text

            team_a = ws.cell(found_row, team_a_idx + 1).value
            team_b = ws.cell(found_row, team_b_idx + 1).value

            msg = f"🎥 {link}\nMatch: **{team_a} vs {team_b}**"
            await ctx.send(msg)
        else:
            await ctx.send(f"❌ No match found for {team1} vs {team2}")

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching match link: {e}")

@bot.command(name="matchinfo")
async def matchinfo(ctx, team1: str, team2: str):
    """Shows a 4‑game breakdown between two teams, including players, stats, and scores."""
    try:
        sheet = get_sheet()
        ws = sheet.worksheet("MATCHES")  # adjust to your sheet/tab name
        all_rows = ws.get_all_values()   # one bulk read

        team1_col = 5   # F
        team2_col = 16  # Q

        found_row = None
        sheet_team1, sheet_team2 = None, None

        # Find the row where these two teams meet, regardless of input order
        for i, row in enumerate(all_rows[1:], start=2):  # skip header
            if len(row) > max(team1_col, team2_col):
                t1 = row[team1_col].strip().lower()
                t2 = row[team2_col].strip().lower()

                # Accept either input order
                if {t1, t2} == {team1.lower(), team2.lower()}:
                    found_row = i
                    sheet_team1, sheet_team2 = row[team1_col].strip(), row[team2_col].strip()
                    break

        if not found_row:
            await ctx.send(f"❌ No match found for {team1} vs {team2}")
            return

        # Grab 4 consecutive rows (games)
        row_data = all_rows[found_row-1 : found_row+3]  # Python is 0-based

        msg_lines = [f"📊 Match Info: **{sheet_team1} vs {sheet_team2}**\n"]
        for offset, row in enumerate(row_data, start=1):
            # Team 1 players + stats
            p1, p1g, p1a = row[6], row[7], row[8]
            p2, p2g, p2a = row[9], row[10], row[11]
            p3, p3g, p3a = row[12], row[13], row[14]

            # Team 2 players + stats
            o1, o1g, o1a = row[17], row[18], row[19]
            o2, o2g, o2a = row[20], row[21], row[22]
            o3, o3g, o3a = row[23], row[24], row[25]

            # Scores
            score1, score2 = row[26], row[27]

            msg_lines.append(
                f"🎮 Game {offset}:\n"
                f"  {sheet_team1} — {p1} (G:{p1g}, A:{p1a}), {p2} (G:{p2g}, A:{p2a}), {p3} (G:{p3g}, A:{p3a})\n"
                f"  {sheet_team2} — {o1} (G:{o1g}, A:{o1a}), {o2} (G:{o2g}, A:{o2a}), {o3} (G:{o3g}, A:{o3a})\n"
                f"  🏆 Score: {sheet_team1} {score1} — {sheet_team2} {score2}\n"
            )

        await ctx.send("\n".join(msg_lines))

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching match info: {e}")

@bot.command(name="assists")
async def assists(ctx):
    """Shows the top 10 assist leaders from the PLAYERS sheet, with GP and goals as tiebreakers."""
    try:
        sheet = get_sheet()
        ws = sheet.worksheet("PLAYERS")
        all_rows = ws.get_all_values()

        # Headers are on row 4 (index 3), data starts at row 5 (index 4)
        headers = [h.strip().lower() for h in all_rows[3]]
        data = all_rows[4:]

        # Find column indexes
        player_idx = headers.index("player")
        team_idx = headers.index("team")
        gp_idx = headers.index("gp")
        g_idx = headers.index("g")
        a_idx = headers.index("a")

        # Parse players
        parsed = []
        for row in data:
            try:
                assists = int(row[a_idx]) if row[a_idx].isdigit() else 0
            except Exception:
                assists = 0
            try:
                gp = int(row[gp_idx]) if row[gp_idx].isdigit() else 0
            except Exception:
                gp = 0
            goals = row[g_idx] if len(row) > g_idx else "0"

            parsed.append({
                "player": row[player_idx],
                "team": row[team_idx],
                "gp": gp,
                "goals": int(goals) if str(goals).isdigit() else 0,
                "assists": assists
            })

        # Sort by assists DESC, GP ASC, goals DESC
        sorted_players = sorted(parsed, key=lambda x: (-x["assists"], x["gp"], -x["goals"]))

        # Build leaderboard text
        msg = "**🅰️ TOP 10 ASSIST LEADERS 🅰️**\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(sorted_players[:10], start=1):
            rank = medals[i-1] if i <= 3 else f"{i}."
            msg += f"{rank} {p['player']} ({p['team']}) - {p['assists']} A, {p['goals']} G, {p['gp']} GP\n"

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching assists: {e}")

print("bot.py loaded")
