# utils.py
import json
import re
import unicodedata
import discord

def carregar_dados():
    try:
        with open('dados.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
            dados.setdefault('assistidos', [])
            dados.setdefault('watchlist', [])
            dados.setdefault('agendamentos', [])
            return dados
    except (FileNotFoundError, json.JSONDecodeError):
        return {"assistidos": [], "watchlist": [], "agendamentos": []}

def salvar_dados(dados):
    with open('dados.json', 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

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