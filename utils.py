# utils.py
import os
import motor.motor_asyncio
import discord
import re
import unicodedata
import certifi # <--- IMPORTA A NOVA FERRAMENTA

# Conecta ao MongoDB usando a URI do ambiente
# --- CORREÇÃO: Adiciona o tlsCAFile para garantir a conexão SSL correta ---
DB_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(
    os.environ['MONGO_URI'],
    tlsCAFile=certifi.where()
)
db = DB_CLIENT.sykocinema # Nome do nosso banco de dados

# Coleções (como se fossem as tabelas)
assistidos_db = db.assistidos
watchlist_db = db.watchlist
agendamentos_db = db.agendamentos

async def setup_database():
    # Cria índices para otimizar as buscas por nome, o que acelera o bot
    await assistidos_db.create_index("nome_sanitizado", unique=True, background=True)
    await watchlist_db.create_index("nome_sanitizado", unique=True, background=True)
    print("Banco de dados conectado e índices verificados.")

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