# main.py
import discord
from discord.ext import commands
import os
from keep_alive import keep_alive
from utils import setup_database
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- CORREÇÃO: Cria uma "trava" para garantir que os Cogs sejam carregados apenas uma vez ---
bot.cogs_loaded = False

@bot.event
async def on_ready():
    # Se os cogs já foram carregados, não faz nada. Evita duplicação em reconexões.
    if bot.cogs_loaded:
        return

    print(f'logado com sucesso como {bot.user}!')
    print(f'versão finalíssima. sem duplicatas.')
    print('------')
    
    await setup_database()

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')
    
    # Ativa a trava para que este bloco de código não rode novamente.
    bot.cogs_loaded = True
    
    if "RENDER" in os.environ:
        print("\n---------------------------------")
        print("O bot está rodando no Render.")
        url_publica = os.environ.get('RENDER_EXTERNAL_URL')
        if url_publica:
            print(f"URL para o UptimeRobot: {url_publica}")
        print("---------------------------------\n")

keep_alive() 
try:
    TOKEN = os.environ['DISCORD_TOKEN']
    if TOKEN: bot.run(TOKEN)
    else: print("Erro: O token do Discord não foi encontrado nos Secrets/Environment.")
except KeyError:
    print("ERRO CRÍTICO: Token não configurado.")