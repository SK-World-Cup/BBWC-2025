import discord
from discord.ext import commands
import os

TOKEN = os.getenv("TOKEN")  # make sure your token is in an environment variable

# Use default intents only (no privileged intents)
intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Example simple command
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run(TOKEN)


