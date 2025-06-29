# utils.py
import os
import motor.motor_asyncio
import discord
import re
import unicodedata
import certifi

# --- CORREÇÃO: Conexão mais robusta com o MongoDB Atlas ---
# Pega a URI de conexão do ambiente
MONGO_URI = os.environ.get('MONGO_URI')

# Cria o cliente com opções explícitas de TLS e usando o certifi
# Esta é a configuração padrão da indústria para evitar erros de SSL
DB_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)
db = DB_CLIENT.sykocinema # Nome do nosso banco de dados

# Coleções (como se fossem as tabelas)
assistidos_db = db.assistidos
watchlist_db = db.watchlist
agendamentos_db = db.agendamentos

async def setup_database():
    try:
        # Tenta enviar um comando simples para verificar a conexão
        await DB_CLIENT.admin.command('ping')
        print("Conexão com o MongoDB estabelecida com sucesso.")
        # Cria índices para otimizar as buscas
        await assistidos_db.create_index("nome_sanitizado", unique=True, background=True)
        await watchlist_db.create_index("nome_sanitizado", unique=True, background=True)
        print("Índices do banco de dados verificados/criados.")
    except Exception as e:
        print(f"ERRO DE CONEXÃO COM O MONGODB: {e}")

def normalizar_texto(texto):
    if not texto: return ""
    s = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return s.lower()

def sanitizar_nome(nome):
    return re.sub(r'[^\w\s]', '', normalizar_texto(nome))

def parse_args(args_str):
    chaves_map = {'nome': 'nome', 'nota': 'nota', 'liked': 'liked', 'comentario': 'comentario', 'comentário': 'comentario', 'genero': 'genero', 'gênero': 'genero', 'escolhido por': 'escolhido por', 'data': 'data', 'ano': 'ano', 'emoji': 'emoji', 'hora': 'hora'}
    padrao_split = r'(' + '|'.join([re.escape(k) + r':?' for k in chaves_map.keys()]) + r')'
    partes = re.split(padrao_split, args_str, flags=re.IGNORECASE)
    dados_capturados = {}
    for i in range(1, len(partes), 2):
        chave = normalizar_texto(partes[i].replace(':', '').strip())
        chave_mapeada = discord.utils.find(lambda k: normalizar_texto(k) == chave, chaves_map.keys())
        if chave_mapeada: dados_capturados[chaves_map[chave_mapeada]] = partes[i+1].strip()
    return dados_capturados