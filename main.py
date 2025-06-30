# main.py
import os
from dotenv import load_dotenv
import asyncio

# --- INÍCIO DO DIAGNÓSTICO ---

print("--- Iniciando Diagnóstico do Ambiente ---")

# Tenta carregar o arquivo .env
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    print("Arquivo .env encontrado no caminho correto.")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("AVISO: Arquivo .env NÃO foi encontrado na pasta do projeto.")

# Pega as variáveis do ambiente
TOKEN = os.environ.get('DISCORD_TOKEN')
MONGO_URI = os.environ.get('MONGO_URI')

# Imprime o status das variáveis
print(f"Token do Discord carregado: {'Sim' if TOKEN else 'Não'}")
print(f"URI do MongoDB carregada: {'Sim' if MONGO_URI else 'Não'}")

if not TOKEN or not MONGO_URI:
    print("\n--- ERRO CRÍTICO ---")
    print("Uma ou mais 'senhas' essenciais não foram carregadas.")
    print("Verifique se o seu arquivo .env está na mesma pasta que o main.py e se os nomes 'DISCORD_TOKEN' e 'MONGO_URI' estão corretos, sem espaços extras.")
    # O bot não vai continuar sem as chaves.
else:
    print("--- Diagnóstico Concluído. Iniciando o bot... ---\n")
    
    # Se tudo estiver ok, o bot continua a partir daqui
    import discord
    from discord.ext import commands
    from keep_alive import keep_alive
    from utils import setup_database

    async def main():
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

        @bot.event
        async def on_ready():
            print(f'logado com sucesso como {bot.user}!')
            print(f'versão 4.0, a versão final com banco de dados. sou imortal.')
            print('------')

        async with bot:
            await setup_database()
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py') and not filename.startswith('__'):
                    try:
                        await bot.load_extension(f'cogs.{filename[:-3]}')
                        print(f'Cog {filename} carregado com sucesso.')
                    except Exception as e:
                        print(f'Falha ao carregar o cog {filename}: {e}')
            
            # A função keep_alive não precisa ser async, então não usamos await
            keep_alive()
            
            await bot.start(TOKEN)

    if __name__ == "__main__":
        try:
            asyncio.run(main())
        except (RuntimeError, KeyboardInterrupt):
            pass # Ignora erros comuns ao parar o bot