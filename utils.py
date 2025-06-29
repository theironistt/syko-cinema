# utils.py
import os
import motor.motor_asyncio
import discord
import re
import unicodedata
import certifi

MONGO_URI = os.environ.get('MONGO_URI')
DB_CLIENT = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = DB_CLIENT.sykocinema

assistidos_db = db.assistidos
watchlist_db = db.watchlist
agendamentos_db = db.agendamentos

async def setup_database():
    try:
        await DB_CLIENT.admin.command('ping')
        print("Conexão com o MongoDB estabelecida com sucesso.")
        # unique=True garante que não teremos filmes com o mesmo nome_sanitizado
        await assistidos_db.create_index("nome_sanitizado", unique=True, background=True)
        await watchlist_db.create_index("nome_sanitizado", unique=True, background=True)
        print("Índices do banco de dados verificados/criados.")
    except Exception as e:
        print(f"ERRO DE CONEXÃO COM O MONGODB: {e}")

def normalizar_texto(texto):
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def sanitizar_nome(nome):
    return re.sub(r'[^\w\s]', '', normalizar_texto(nome))

# --- CORREÇÃO FINAL: O Parser Inteligente ---
def parse_args(args_str):
    # Lista de palavras-chave que definem os campos
    chaves = ['nome', 'nota', 'liked', 'comentario', 'comentário', 'genero', 'gênero', 'escolhido por', 'data', 'ano', 'emoji', 'hora']
    
    # Mapa para normalizar as chaves (ex: comentário e comentario viram 'comentario')
    chaves_map = {
        'nome': 'nome', 'nota': 'nota', 'liked': 'liked', 'comentario': 'comentario', 
        'comentário': 'comentario', 'genero': 'genero', 'gênero': 'genero', 
        'escolhido por': 'escolhido por', 'data': 'data', 'ano': 'ano', 
        'emoji': 'emoji', 'hora': 'hora'
    }

    # Expressão regular que procura pelas palavras-chave seguidas por ':'
    # Isso evita que ele se confunda com palavras dentro de frases.
    padrao_split = r'\b(' + '|'.join(re.escape(k) for k in chaves) + r'):'
    
    # Divide a string de argumentos usando o padrão
    partes = re.split(padrao_split, args_str, flags=re.IGNORECASE)
    
    # O primeiro item é o que vem antes do primeiro campo (geralmente lixo ou o nome do filme se não usar 'nome:')
    # Nós podemos tentar usar isso como o nome se o campo 'nome' não for achado.
    primeiro_bloco = partes[0].strip()
    
    dados_capturados = {}
    
    # Processa os pares de chave-valor
    for i in range(1, len(partes), 2):
        chave_norm = normalizar_texto(partes[i])
        chave_mapeada = chaves_map.get(chave_norm)
        if chave_mapeada:
            valor = partes[i+2].strip()
            dados_capturados[chave_mapeada] = valor

    # Se 'nome' não foi capturado via 'nome:', usa o primeiro bloco de texto
    if 'nome' not in dados_capturados and primeiro_bloco:
        dados_capturados['nome'] = primeiro_bloco
        
    return dados_capturados