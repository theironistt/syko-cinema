# cogs/catalogo.py
import discord
from discord.ext import commands
import random
from datetime import datetime
from utils import assistidos_db, watchlist_db, normalizar_texto, sanitizar_nome, parse_args

class Catalogo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='assistido')
    async def _assistido(self, ctx, *, argumentos_str: str):
        try:
            dados_capturados = parse_args(argumentos_str)
            nome_filme = dados_capturados.get('nome')
            if not nome_filme: return await ctx.send('o campo `nome` é essencial.')
            
            nome_filme_sanitizado = sanitizar_nome(nome_filme)
            if await assistidos_db.find_one({'nome_sanitizado': nome_filme_sanitizado}):
                return await ctx.send("eita, parece que esse filme já tá na nossa lista de assistidos.")

            nota_str, genero = dados_capturados.get('nota'), dados_capturados.get('genero')
            if not nota_str or not genero: return await ctx.send('preciso pelo menos de `nome`, `nota` e `genero`.')

            novo_filme = {
                'nome': nome_filme.strip(),
                'nome_sanitizado': nome_filme_sanitizado,
                'nota': float(nota_str.replace(',', '.')),
                'like': '🌟' if dados_capturados.get('liked', '').lower() == 'sim' else '—',
                'genero': genero,
                'comentario': dados_capturados.get('comentario', 'sem comentários.'),
                'data': dados_capturados.get('data', datetime.now().strftime('%d/%m/%Y')),
                'ano': dados_capturados.get('ano', ''),
                'emoji': dados_capturados.get('emoji', ''),
                'adicionado_por': ctx.author.id
            }
            
            escolhido_por_str = dados_capturados.get('escolhido por')
            if escolhido_por_str:
                membro = discord.utils.find(lambda m: normalizar_texto(m.display_name).startswith(normalizar_texto(escolhido_por_str)), ctx.guild.members)
                novo_filme['escolhido_por'] = membro.id if membro else escolhido_por_str
            else:
                novo_filme['escolhido_por'] = ctx.author.id

            # Insere no banco de dados
            await assistidos_db.insert_one(novo_filme)
            
            # Remove da watchlist se existir
            resultado_remocao = await watchlist_db.delete_one({'nome_sanitizado': nome_filme_sanitizado})
            
            nome_autor = ctx.author.display_name
            if resultado_remocao.deleted_count > 0:
                await ctx.send(f"perfeito, {nome_autor}! '{nome_filme.strip()}' foi assistido e já risquei ele da nossa watchlist interminável.")
            else:
                respostas = [f"anotado, {nome_autor}. '{nome_filme.strip()}' agora faz parte da nossa história. tipo, sei lá, o ed e lorraine, só que com menos drama e demonios. eu acho.", f"feito, {nome_autor}! '{nome_filme.strip()}' foi devidamente catalogado na nossa estante virtual. espero que a crítica bianca precinotto aprove.", f"registrado, {nome_autor}. a gente agora tem uma entrada nova no diário de bordo sobre '{nome_filme.strip()}'. também vou assistir depois e conto pra vocês se gostei. tomara que seja um clássico cult."]
                await ctx.send(random.choice(respostas))
        except ValueError:
            await ctx.send(f"hm, {ctx.author.display_name}, essa nota aí tá esquisita. `nota:` precisa ser um número.")
        except Exception as e:
            print(f"Ocorreu um erro no !assistido: {e}")
            await ctx.send("deu um bug geral na matrix.")

async def setup(bot):
    await bot.add_cog(Catalogo(bot))