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

# --- CORREÇÃO FINALÍSSIMA: Parser totalmente reescrito para ser mais robusto ---
def parse_args(args_str):
    # Define as palavras-chave que estamos procurando e seus sinônimos
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
    
    # Encontra todas as ocorrências das chaves e suas posições
    matches = list(padrao.finditer(args_str))
    
    # Se não há chaves, tudo é o nome.
    if not matches:
        if args_str: dados_capturados['nome'] = args_str.strip()
        return dados_capturados

    # Se houver texto ANTES da primeira chave, ele é o nome.
    primeiro_match = matches[0]
    texto_antes = args_str[:primeiro_match.start()].strip()
    if texto_antes:
        dados_capturados['nome'] = texto_antes
        
    # Itera sobre as chaves encontradas para extrair seus valores
    for i, match_atual in enumerate(matches):
        chave_encontrada = normalizar_texto(match_atual.group(1))
        chave_mapeada = chaves_map.get(chave_encontrada)
        
        if not chave_mapeada: continue

        # Define o início do valor
        inicio_valor = match_atual.end()
        
        # Define o fim do valor (o início da próxima chave, ou o final da string)
        if i + 1 < len(matches):
            proximo_match = matches[i+1]
            fim_valor = proximo_match.start()
        else:
            fim_valor = len(args_str)
            
        valor = args_str[inicio_valor:fim_valor].strip()
        
        # Se a chave for 'nome', o valor pode ter sido capturado antes, então só atualiza se estiver vazio.
        if chave_mapeada == 'nome':
            if 'nome' not in dados_capturados:
                dados_capturados[chave_mapeada] = valor
        else:
            dados_capturados[chave_mapeada] = valor
            
    return dados_capturados