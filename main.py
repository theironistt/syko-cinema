# main.py
import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive
from utils import setup_database
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.initialized = False

@bot.event
async def on_ready():
    if bot.initialized:
        return

    print(f'Logado como {bot.user}!')
    await setup_database()

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado.')
            except Exception as e:
                print(f'Erro ao carregar cog {filename}: {e}')

    bot.initialized = True
    print("--- Bot está pronto! ---")

async def start_bot():
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("Token do Discord não encontrado.")
        return

    await bot.start(token)

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(start_bot())
    except Exception as e:
        print(f"Erro ao iniciar o bot: {e}")
