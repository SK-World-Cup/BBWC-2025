import os
import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from threading import Thread

# ====== Discord Bot Setup ======
intents = discord.Intents.default()
intents.message_content = True  # required for ! commands

bot = commands.Bot(command_prefix="!", intents=intents)

# ====== Google Sheets Setup ======
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_file = "credentials.json"  # make sure this file is in your repo
credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
gc = gspread.authorize(credentials)

# Replace with your actual Sheet ID
sheet_id = os.getenv("SHEET_ID")  
sheet = gc.open_by_key(sheet_id)

# ====== Commands ======
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# ====== Flask Webserver ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!", 200

def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Run Flask in a separate thread so bot and webserver run together
Thread(target=run_webserver).start()

# ====== Run Bot ======
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

