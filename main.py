# main.py
import discord
from discord.ext import commands
import os
import asyncio
from keep_alive import keep_alive
from utils import setup_database
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para testes locais
load_dotenv()

# Configuração do Bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Uma trava para garantir que a inicialização completa só aconteça uma vez
bot.initialized = False

@bot.event
async def on_ready():
    """
    Este evento é chamado quando o bot se conecta com sucesso ao Discord.
    É o local perfeito para carregar as funcionalidades secundárias.
    """
    # Se o bot já inicializou (ex: em uma reconexão), não faz nada.
    if bot.initialized:
        return

    print(f'logado com sucesso como {bot.user}!')
    print(f'versão final. estável, único e pronto para o serviço.')
    print('------')
    
    # 1. Conecta ao banco de dados
    await setup_database()

    # 2. Carrega todos os seus comandos (Cogs)
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and not filename.startswith('__'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Cog {filename} carregado com sucesso.')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {e}')
    
    # 3. Marca o bot como 100% inicializado
    bot.initialized = True
    print("--- bot pronto e operacional! ---")

async def main():
    # Inicia o servidor web em segundo plano para o UptimeRobot
    keep_alive()
    
    try:
        TOKEN = os.environ['DISCORD_TOKEN']
        if TOKEN:
            # O bot tentará se conectar ao Discord com o token
            await bot.start(TOKEN)
        else:
            print("Erro: O token do Discord não foi encontrado nos Secrets/Environment.")
    except KeyError:
        print("ERRO CRÍTICO: Token não configurado. Verifique os Secrets no Render ou seu arquivo .env local.")

# Ponto de partida do programa
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        pass # Ignora erros comuns ao parar o bot com CTRL+C