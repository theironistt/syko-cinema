# main.py
import discord
from discord.ext import commands
import os
from keep_alive import keep_alive # Importa a função do nosso servidor web

# --- Configuração Inicial ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- Evento on_ready ---
@bot.event
async def on_ready():
    print(f'logado com sucesso como {bot.user}!')
    print(f'versão 3.2, a definitiva. pronto para ser nosso cineclube particular.')
    print('------')
    # Carrega todas as "gavetas" (Cogs) da pasta /cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')

    # --- NOVO TRECHO DE CÓDIGO ---
    # Pega a URL pública do Replit e imprime no console para o UptimeRobot
    # A variável de ambiente REPL_IT_URL é fornecida automaticamente pelo Replit
    if "REPL_ID" in os.environ:
        print("\n---------------------------------")
        print("O bot está rodando no Replit.")
        print(f"URL para o UptimeRobot: {os.environ['REPL_IT_URL']}")
        print("---------------------------------\n")

# --- Execução do Bot ---

# Inicia o servidor web para manter o bot acordado
keep_alive() 

# Pega o token do ambiente seguro do Replit
TOKEN = os.environ['DISCORD_TOKEN']
bot.run(TOKEN)