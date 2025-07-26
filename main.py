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

    print(f'Logado com sucesso como {bot.user}!')
    print(f'Versão final e estável. Pronto para catalogar!')
    print('------')

    await setup_database()

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')

    bot.initialized = True
    print("--- Bot pronto e operacional! ---")

async def main():
    keep_alive()  # Inicia o servidor Flask (para UptimeRobot)

    try:
        TOKEN = os.environ.get("DISCORD_TOKEN")
        if TOKEN:
            # Pequeno delay ajuda a evitar bloqueio de IP compartilhado na inicialização
            await asyncio.sleep(5)
            await bot.start(TOKEN)
        else:
            print("Erro: o token do Discord não foi encontrado na variável DISCORD_TOKEN.")
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("\n--- ERRO DE RATE LIMIT ---")
            print("O bot está temporariamente bloqueado pelo Discord por muitas tentativas de conexão.")
            print("Isso geralmente é causado por um problema no IP do servidor de hospedagem.")
            print("Aguarde alguns minutos ou use outra plataforma (como Railway) para obter um IP diferente.")
        else:
            raise e
    except Exception as e:
        print(f"Erro inesperado: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        pass
