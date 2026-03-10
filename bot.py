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
from time import time, sleep
import requests

# We'll use a hybrid approach - try gspread first, fall back to direct CSV
class PublicSheet:
    def __init__(self, sheet_id):
        self.sheet_id = sheet_id
        
    def get_worksheet(self, sheet_name):
        """Get worksheet data as list of lists"""
        url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse CSV
        import csv
        from io import StringIO
        
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        return list(reader)

# Initialize public sheet access
SHEET_ID = os.environ.get("SHEET_ID")
if not SHEET_ID:
    raise RuntimeError("SHEET_ID not set")

public_sheet = PublicSheet(SHEET_ID)

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

@bot.command(name="player")
async def player(ctx, *, name: str):
    """Displays stats for a specific player from the PLAYERS sheet."""
    try:
        # Get worksheet data
        all_rows = public_sheet.get_worksheet("PLAYERS")
        
        # Headers are on row 4 (index 3), data starts at row 5 (index 4)
        headers = all_rows[3]
        data_rows = all_rows[4:]

        # Column indexes (0-based)
        # C4: Players (index 2), E4: TEAM (index 4), F4: GP (index 5), J4: G (index 9), K4: A (index 10)
        player_idx = 2  # Column C
        team_idx = 4    # Column E
        gp_idx = 5      # Column F
        goals_idx = 9   # Column J
        assists_idx = 10 # Column K

        # Find the player's row (case-insensitive match)
        player_row = None
        for row in data_rows:
            if len(row) > player_idx and row[player_idx].strip().lower() == name.lower():
                player_row = row
                break

        if not player_row:
            await ctx.send(f"❌ Player '{name}' not found.")
            return

        # Get values with safe indexing
        player_name = player_row[player_idx] if len(player_row) > player_idx else "Unknown"
        team = player_row[team_idx] if len(player_row) > team_idx else "Unknown"
        gp = player_row[gp_idx] if len(player_row) > gp_idx else "0"
        goals = player_row[goals_idx] if len(player_row) > goals_idx else "0"
        assists = player_row[assists_idx] if len(player_row) > assists_idx else "0"

        # Build stats message (simplified since we only have basic stats)
        msg = (
            f"**{player_name}** ({team})\n"
            f"Games: {gp} | Goals: {goals} | Assists: {assists}"
        )

        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"⚠️ Error fetching player data: {e}")

@bot.command(name="standings")
async def standings(ctx):
    """Shows the tournament standings of every team sorted by points."""
    try:
        all_rows = public_sheet.get_worksheet("GROUP_STAGE")

        # Headers are on row 7 (index 6), data starts at row 8 (index 7)
        headers = all_rows[6]
        data = all_rows[7:]

        # Column indexes (0-based)
        # C7: Team (index 2), E7: GP (index 4), F7: W (index 5), G7: D (index 6), 
        # H7: L (index 7), J7: GF (index 9), K7: GA (index 10), Q7: PTS (index 16)
        team_idx = 2   # Column C
        gp_idx = 4     # Column E
        w_idx = 5      # Column F
        d_idx = 6      # Column G
        l_idx = 7      # Column H
        gf_idx = 9     # Column J
        ga_idx = 10    # Column K
        pts_idx = 16   # Column Q

        # Parse data and sort by PTS descending
        parsed = []
        for row in data:
            if len(row) > team_idx and row[team_idx].strip():  # Only process rows with team names
                try:
                    pts = int(row[pts_idx]) if len(row) > pts_idx and row[pts_idx].strip() else 0
                except (ValueError, IndexError):
                    pts = 0
                
                parsed.append({
                    "team": row[team_idx] if len(row) > team_idx else "",
                    "gp": row[gp_idx] if len(row) > gp_idx else "0",
                    "w": row[w_idx] if len(row) > w_idx else "0",
                    "d": row[d_idx] if len(row) > d_idx else "0",
                    "l": row[l_idx] if len(row) > l_idx else "0",
                    "gf": row[gf_idx] if len(row) > gf_idx else "0",
                    "ga": row[ga_idx] if len(row) > ga_idx else "0",
                    "gd": str(int(row[gf_idx] if len(row) > gf_idx and row[gf_idx].strip() else 0) - 
                             int(row[ga_idx] if len(row) > ga_idx and row[ga_idx].strip() else 0)),
                    "pts": pts
                })

        # Filter out empty teams and sort
        parsed = [t for t in parsed if t["team"]]
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
        # Get players data
        players_rows = public_sheet.get_worksheet("PLAYERS")
        standings_rows = public_sheet.get_worksheet("GROUP_STAGE")

        # ---- Get Player List ----
        # Headers on row 4 (index 3)
        headers = [h.strip().lower() for h in players_rows[3]]
        
        # Column indexes
        player_col = 2  # Column C
        team_col = 4    # Column E
        gp_col = 5      # Column F
        goals_col = 9   # Column J
        assists_col = 10 # Column K

        players_data = []
        for row in players_rows[4:]:  # Data starts at row 5
            if len(row) > team_col and row[team_col].strip().lower() == team_name.lower():
                player_name = row[player_col] if len(row) > player_col else "Unknown"
                gp = row[gp_col] if len(row) > gp_col else "0"
                g = row[goals_col] if len(row) > goals_col else "0"
                a = row[assists_col] if len(row) > assists_col else "0"
                players_data.append(f"{player_name}: {gp} GP | {g} G | {a} A")

        if not players_data:
            await ctx.send(f"⚠️ No players found for **{team_name}**.")
            return

        # ---- Get Team Totals ----
        # Headers on row 7 (index 6)
        headers2 = [h.strip().lower() for h in standings_rows[6]]
        data = standings_rows[7:]  # Data starts at row 8

        team_idx = 2  # Column C
        totals = None
        for row in data:
            if len(row) > team_idx and row[team_idx].strip().lower() == team_name.lower():
                # Column indexes for team totals
                gp = row[4] if len(row) > 4 else "0"   # Column E
                w = row[5] if len(row) > 5 else "0"    # Column F
                d = row[6] if len(row) > 6 else "0"    # Column G
                l = row[7] if len(row) > 7 else "0"    # Column H
                gf = row[9] if len(row) > 9 else "0"   # Column J
                ga = row[10] if len(row) > 10 else "0" # Column K
                pts = row[16] if len(row) > 16 else "0" # Column Q
                
                totals = {
                    "gp": gp,
                    "w": w,
                    "d": d,
                    "l": l,
                    "gf": gf,
                    "ga": ga,
                    "gd": str(int(gf) - int(ga)) if gf.isdigit() and ga.isdigit() else "0",
                    "pts": pts,
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
        all_rows = public_sheet.get_worksheet("PLAYERS")

        # Headers are on row 4 (index 3), data starts at row 5 (index 4)
        headers = [h.strip().lower() for h in all_rows[3]]
        data = all_rows[4:]

        # Column indexes
        player_idx = 2  # Column C
        team_idx = 4    # Column E
        gp_idx = 5      # Column F
        g_idx = 9       # Column J
        a_idx = 10      # Column K

        # Parse players
        parsed = []
        for row in data:
            if len(row) > player_idx and row[player_idx].strip():  # Only process rows with player names
                try:
                    goals = int(row[g_idx]) if len(row) > g_idx and row[g_idx].strip().isdigit() else 0
                except Exception:
                    goals = 0
                try:
                    gp = int(row[gp_idx]) if len(row) > gp_idx and row[gp_idx].strip().isdigit() else 0
                except Exception:
                    gp = 0
                assists = row[a_idx] if len(row) > a_idx and row[a_idx].strip() else "0"

                parsed.append({
                    "player": row[player_idx] if len(row) > player_idx else "Unknown",
                    "team": row[team_idx] if len(row) > team_idx else "Unknown",
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

@bot.command(name="matchlink")
async def matchlink(ctx, team1: str, team2: str):
    """Provides the video link for a match between two teams."""
    try:
        all_rows = public_sheet.get_worksheet("MATCHES")

        # Column indexes (0-based: D=3, F=5, Q=16)
        link_idx = 3
        team_a_idx = 5
        team_b_idx = 16

        found_row = None
        found_data = None
        
        for i, row in enumerate(all_rows[1:], start=1):  # skip header
            if len(row) > max(link_idx, team_a_idx, team_b_idx):
                t_a = row[team_a_idx].strip().lower()
                t_b = row[team_b_idx].strip().lower()
                if {t_a, t_b} == {team1.lower(), team2.lower()}:
                    found_data = row
                    break

        if found_data:
            link = found_data[link_idx] if len(found_data) > link_idx else "No link available"
            team_a = found_data[team_a_idx] if len(found_data) > team_a_idx else team1
            team_b = found_data[team_b_idx] if len(found_data) > team_b_idx else team2

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
        all_rows = public_sheet.get_worksheet("MATCHES")

        team1_col = 5   # F
        team2_col = 16  # Q

        found_index = None
        sheet_team1, sheet_team2 = None, None

        # Find the row where these two teams meet, regardless of input order
        for i, row in enumerate(all_rows[1:], start=1):  # skip header
            if len(row) > max(team1_col, team2_col):
                t1 = row[team1_col].strip().lower()
                t2 = row[team2_col].strip().lower()

                # Accept either input order
                if {t1, t2} == {team1.lower(), team2.lower()}:
                    found_index = i
                    sheet_team1, sheet_team2 = row[team1_col].strip(), row[team2_col].strip()
                    break

        if found_index is None:
            await ctx.send(f"❌ No match found for {team1} vs {team2}")
            return

        # Grab 4 consecutive rows (games)
        start_idx = found_index
        end_idx = min(found_index + 4, len(all_rows))
        row_data = all_rows[start_idx:end_idx]

        msg_lines = [f"📊 Match Info: **{sheet_team1} vs {sheet_team2}**\n"]
        for offset, row in enumerate(row_data, start=1):
            # Ensure row has enough columns
            if len(row) < 28:
                continue
                
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
        all_rows = public_sheet.get_worksheet("PLAYERS")

        # Headers are on row 4 (index 3), data starts at row 5 (index 4)
        headers = [h.strip().lower() for h in all_rows[3]]
        data = all_rows[4:]

        # Column indexes
        player_idx = 2  # Column C
        team_idx = 4    # Column E
        gp_idx = 5      # Column F
        g_idx = 9       # Column J
        a_idx = 10      # Column K

        # Parse players
        parsed = []
        for row in data:
            if len(row) > player_idx and row[player_idx].strip():  # Only process rows with player names
                try:
                    assists = int(row[a_idx]) if len(row) > a_idx and row[a_idx].strip().isdigit() else 0
                except Exception:
                    assists = 0
                try:
                    gp = int(row[gp_idx]) if len(row) > gp_idx and row[gp_idx].strip().isdigit() else 0
                except Exception:
                    gp = 0
                try:
                    goals = int(row[g_idx]) if len(row) > g_idx and row[g_idx].strip().isdigit() else 0
                except Exception:
                    goals = 0

                parsed.append({
                    "player": row[player_idx] if len(row) > player_idx else "Unknown",
                    "team": row[team_idx] if len(row) > team_idx else "Unknown",
                    "gp": gp,
                    "goals": goals,
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

@bot.command(name="redebug_sheet")
async def debug_sheet(ctx):
    """Debug command to see the actual sheet structure (compact version)"""
    try:
        all_rows = public_sheet.get_worksheet("GROUP_STAGE")
        
        # Send row count first
        await ctx.send(f"📊 GROUP_STAGE has {len(all_rows)} total rows")
        
        # Send headers info in chunks
        msg = "**Row structure (first 15 rows):**\n```\n"
        for i in range(min(15, len(all_rows))):
            row = all_rows[i]
            # Only show first 3 columns and any column with "Team", "GP", "PTS" etc.
            preview = []
            for j, cell in enumerate(row[:10]):  # Look at first 10 columns
                if cell and str(cell).strip():
                    cell_str = str(cell).strip()
                    if len(cell_str) > 15:
                        cell_str = cell_str[:12] + "..."
                    preview.append(f"{chr(65+j)}:{cell_str}")  # Show column letter
            if preview:
                msg += f"Row {i}: {' | '.join(preview)}\n"
        
        msg += "```"
        
        # Split if too long
        if len(msg) > 1900:
            await ctx.send("First part:")
            await ctx.send(msg[:1900])
            await ctx.send("Second part:")
            await ctx.send(msg[1900:])
        else:
            await ctx.send(msg)
        
        # Look specifically for rows with team names
        await ctx.send("**Looking for team data:**")
        team_rows = []
        for i, row in enumerate(all_rows):
            for j, cell in enumerate(row[:10]):  # Check first 10 columns
                if cell and str(cell).strip() and len(str(cell).strip()) > 2:
                    cell_upper = str(cell).upper().strip()
                    # Common team names or header keywords
                    if cell_upper in ["ASIA", "EUROPE", "USA", "CANADA", "UK", "TEAM", "GP", "PTS"]:
                        team_rows.append(f"Row {i}, Col {chr(65+j)}: '{cell}'")
                        break
        
        if team_rows:
            await ctx.send("Potential team/header locations:\n" + "\n".join(team_rows[:10]))
        else:
            await ctx.send("No obvious team names found in first 10 columns")
            
    except Exception as e:
        await ctx.send(f"⚠️ Error: {e}")

print("bot.py loaded")
