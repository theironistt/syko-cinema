# main.py
import discord
from discord.ext import commands
import os
from keep_alive import keep_alive
from utils import setup_database
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'logado com sucesso como {bot.user}!')
    print(f'versão 5.0, a versão final com banco de dados MongoDB. sou imortal.')
    print('------')
    
    await setup_database()

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')

keep_alive() 
try:
    TOKEN = os.environ['DISCORD_TOKEN']
    if TOKEN: bot.run(TOKEN)
    else: print("Erro: O token do Discord não foi encontrado.")
except KeyError:
    print("ERRO CRÍTICO: Token não configurado.")