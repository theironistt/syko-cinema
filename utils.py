# utils.py
import os
import motor.motor_asyncio
import discord
import re
import unicodedata
import certifi

MONGO_URI = os.environ.get('MONGO_URI')
DB_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)
db = DB_CLIENT.sykocinema

# Nossas "tabelas" no banco de dados
assistidos_db = db.assistidos
watchlist_db = db.watchlist
agendamentos_db = db.agendamentos
configuracoes_db = db.configuracoes # <-- NOVA COLEÇÃO

async def setup_database():
    try:
        await DB_CLIENT.admin.command('ping')
        print("Conexão com o MongoDB estabelecida com sucesso.")
        await assistidos_db.create_index("nome_sanitizado", unique=True, background=True)
        await watchlist_db.create_index("nome_sanitizado", unique=True, background=True)
        print("Índices do banco de dados verificados/criados.")
    except Exception as e:
        print(f"ERRO DE CONEXÃO COM O MONGODB: {e}")

def normalizar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def sanitizar_nome(nome):
    nome = nome.lower()
    nome = unicodedata.normalize('NFD', nome)
    nome = nome.encode('ascii', 'ignore').decode('utf-8')
    nome = re.sub(r'[^a-z0-9]+', ' ', nome).strip()
    return nome

def parse_args(args_str):
    chaves = ['nome', 'nota', 'liked', 'comentario', 'comentário', 'genero', 'gênero', 'escolhido por', 'data', 'ano', 'emoji', 'hora']
    chaves_map = {
        'nome': 'nome', 'nota': 'nota', 'liked': 'liked', 'comentario': 'comentario', 'comentário': 'comentario',
        'genero': 'genero', 'gênero': 'genero', 'escolhido por': 'escolhido por', 'data': 'data', 
        'ano': 'ano', 'emoji': 'emoji', 'hora': 'hora'
    }
    padrao = re.compile(r'\b(' + '|'.join(chaves) + r'):', re.IGNORECASE)
    dados_capturados = {}
    ultimo_indice = len(args_str)
    matches = list(padrao.finditer(args_str))
    for i in range(len(matches) - 1, -1, -1):
        match_atual = matches[i]
        chave_encontrada = normalizar_texto(match_atual.group(1))
        chave_mapeada = chaves_map.get(chave_encontrada)
        inicio_valor = match_atual.end()
        valor = args_str[inicio_valor:ultimo_indice].strip()
        if chave_mapeada: dados_capturados[chave_mapeada] = valor
        ultimo_indice = match_atual.start()
    texto_antes = args_str[:ultimo_indice].strip()
    if texto_antes and 'nome' not in dados_capturados:
        dados_capturados['nome'] = texto_antes
    return dados_capturados