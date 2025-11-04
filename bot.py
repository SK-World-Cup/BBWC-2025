import discord
from discord.ext import commands
import os
import gspread
from google.oauth2.service_account import Credentials
import time

TOKEN = os.getenv("TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS_JSON")  # JSON string of your service account

# Discord bot setup without privileged intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Google Sheets setup
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_info(eval(GOOGLE_CREDS), scopes=scopes)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID).sheet1
except Exception as e:
    print(f"Error loading Google Sheet: {e}")
    sheet = None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Ping command to check latency
@bot.command()
async def ping(ctx):
    start = time.perf_counter()
    msg = await ctx.send("Pong!")
    end = time.perf_counter()
    latency_ms = (end - start) * 1000
    await msg.edit(content=f"Pong! Response time: {latency_ms:.2f}ms")

# Read a cell
@bot.command()
async def readcell(ctx, cell="A1"):
    if sheet:
        try:
            value = sheet.acell(cell).value
            await ctx.send(f"Value at {cell}: {value}")
        except Exception as e:
            await ctx.send(f"Error reading cell: {e}")
    else:
        await ctx.send("Google Sheet not loaded.")

# Write to a cell
@bot.command()
async def writecell(ctx, cell, *, value):
    if sheet:
        try:
            sheet.update(cell, value)
            await ctx.send(f"Updated {cell} to {value}")
        except Exception as e:
            await ctx.send(f"Error updating cell: {e}")
    else:
        await ctx.send("Google Sheet not loaded.")

bot.run(TOKEN)
