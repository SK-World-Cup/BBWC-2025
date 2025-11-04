import os
import json
import discord
from discord.ext import commands
import gspread
from google.oauth2.service_account import Credentials

# ---- Discord Setup ----
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ---- Google Sheets Setup ----
creds_json = os.getenv("GOOGLE_CREDS_JSON")
sheet_id = os.getenv("GOOGLE_SHEET_ID")

if not creds_json or not sheet_id:
    raise RuntimeError("Missing GOOGLE_CREDS_JSON or GOOGLE_SHEET_ID environment variables!")

creds_info = json.loads(creds_json)
creds = Credentials.from_service_account_info(
    creds_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(sheet_id)

# ---- Events ----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# ---- Basic Commands ----
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command(name="sheet_test")
async def sheet_test(ctx):
    """Reads cell A1 from the first sheet (for testing)."""
    try:
        ws = sheet.sheet1
        value = ws.acell("A1").value
        await ctx.send(f"Cell A1 = {value}")
    except Exception as e:
        await ctx.send(f"Error reading sheet: {e}")

# ---- Run Bot ----
bot.run(TOKEN)

