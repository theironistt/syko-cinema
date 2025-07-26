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

# Uma trava para garantir que a inicialização só aconteça uma vez
bot.initialized = False

@bot.event
async def on_ready():
    # Se o bot já inicializou, não faz nada (evita problemas em reconexões)
    if bot.initialized:
        return

    print(f'logado com sucesso como {bot.user}!')
    print(f'versão 5.0, a versão final com banco de dados. sou imortal.')
    print('------')
    
    # 1. Conecta ao banco de dados
    await setup_database()

    # 2. Carrega todos os comandos (Cogs)
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')
    
    # 3. Marca o bot como inicializado
    bot.initialized = True
    print("--- Bot pronto e operacional! ---")

async def main():
    # Inicia o servidor web ANTES de tudo
    keep_alive()
    
    try:
        TOKEN = os.environ['DISCORD_TOKEN']
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("Erro: O token do Discord não foi encontrado.")
    except KeyError:
        print("ERRO CRÍTICO: Token não configurado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        pass # Ignora erros comuns ao parar o bot