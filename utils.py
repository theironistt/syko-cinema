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

assistidos_db = db.assistidos
watchlist_db = db.watchlist
agendamentos_db = db.agendamentos

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
    return re.sub(r'[^\w\s]', '', normalizar_texto(nome))

# --- CORREÇÃO FINAL: Parser totalmente reescrito para ser mais robusto ---
def parse_args(args_str):
    # Define as palavras-chave que estamos procurando
    chaves = ['nome', 'nota', 'liked', 'comentario', 'comentário', 'genero', 'gênero', 'escolhido por', 'data', 'ano', 'emoji', 'hora']
    
    # Mapa para normalizar chaves (ex: comentário vira comentario)
    chaves_map = {
        'nome': 'nome', 'nota': 'nota', 'liked': 'liked', 'comentario': 'comentario', 'comentário': 'comentario',
        'genero': 'genero', 'gênero': 'genero', 'escolhido por': 'escolhido por', 'data': 'data', 
        'ano': 'ano', 'emoji': 'emoji', 'hora': 'hora'
    }

    # Cria um padrão de busca para encontrar qualquer uma das chaves (com ou sem :)
    padrao = re.compile(r'\b(' + '|'.join(chaves) + r'):?', re.IGNORECASE)
    
    dados_capturados = {}
    ultimo_indice = 0
    
    # Encontra a primeira chave para saber onde o texto principal começa
    primeiro_match = padrao.search(args_str)
    
    # Se nenhuma chave for encontrada, toda a string é o 'nome'
    if not primeiro_match:
        if args_str:
            dados_capturados['nome'] = args_str.strip()
        return dados_capturados
    
    # Se houver texto antes da primeira chave, ele é o 'nome'
    texto_antes = args_str[:primeiro_match.start()].strip()
    if texto_antes:
        dados_capturados['nome'] = texto_antes
        
    # Itera sobre todas as chaves encontradas na string
    for match in padrao.finditer(args_str):
        # Normaliza a chave encontrada para o nosso padrão
        chave_encontrada = normalizar_texto(match.group(1))
        chave_mapeada = chaves_map.get(chave_encontrada)
        
        # Pega o texto entre a chave atual e a próxima
        inicio_valor = match.end()
        proximo_match = padrao.search(args_str, inicio_valor)
        fim_valor = proximo_match.start() if proximo_match else len(args_str)
        
        valor = args_str[inicio_valor:fim_valor].strip()
        
        if chave_mapeada:
            dados_capturados[chave_mapeada] = valor
            
    return dados_capturados