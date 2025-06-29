# cogs/catalogo.py
import discord
from discord.ext import commands
import random
from datetime import datetime
from utils import carregar_dados, salvar_dados, normalizar_texto, sanitizar_nome, parse_args

class Catalogo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='assistido')
    async def _assistido(self, ctx, *, argumentos_str: str):
        try:
            dados_capturados = parse_args(argumentos_str)
            nome_filme = dados_capturados.get('nome')
            if not nome_filme: return await ctx.send('o campo `nome` é essencial.')

            dados_db = carregar_dados()
            if any(sanitizar_nome(f['nome']) == sanitizar_nome(nome_filme) for f in dados_db['assistidos']):
                return await ctx.send("eita, parece que esse filme já tá na nossa lista de assistidos.")

            nota_str, genero = dados_capturados.get('nota'), dados_capturados.get('genero')
            if not nota_str or not genero: return await ctx.send('preciso pelo menos de `nome`, `nota` e `genero`.')

            nota_final = float(nota_str.replace(',', '.'))
            like_final = '🌟' if dados_capturados.get('liked', '').lower() == 'sim' else '—'
            comentario = dados_capturados.get('comentario', 'sem comentários.')
            data_filme = dados_capturados.get('data', datetime.now().strftime('%d/%m/%Y'))
            ano_filme = dados_capturados.get('ano', '')
            emojis_filme = dados_capturados.get('emoji', '')

            escolhido_por_str = dados_capturados.get('escolhido por')
            escolhido_por_final = ctx.author.id
            if escolhido_por_str:
                membro = discord.utils.find(lambda m: normalizar_texto(m.display_name).startswith(normalizar_texto(escolhido_por_str)), ctx.guild.members)
                if membro: escolhido_por_final = membro.id
                else: escolhido_por_final = escolhido_por_str

            filme_removido = any(sanitizar_nome(item['nome']) == sanitizar_nome(nome_filme) for item in dados_db.get('watchlist', []))
            dados_db['watchlist'] = [item for item in dados_db.get('watchlist', []) if sanitizar_nome(item['nome']) != sanitizar_nome(nome_filme)]

            novo_filme = { 'nome': nome_filme.strip(), 'nota': nota_final, 'like': like_final, 'genero': genero, 'comentario': comentario, 'escolhido_por': escolhido_por_final, 'data': data_filme, 'adicionado_por': ctx.author.id, 'ano': ano_filme, 'emoji': emojis_filme }
            dados_db['assistidos'].append(novo_filme)
            salvar_dados(dados_db)

            nome_autor = ctx.author.display_name
            nome_filme_formatado = nome_filme.strip()

            if filme_removido:
                await ctx.send(f"perfeito, {nome_autor}! '{nome_filme_formatado}' foi assistido e já risquei ele da nossa watchlist interminável.")
            else:
                # --- CORREÇÃO FINAL: SUAS RESPOSTAS PERSONALIZADAS DE VOLTA! ---
                respostas = [
                    f"anotado, {nome_autor}. '{nome_filme_formatado}' agora faz parte da nossa história. tipo, sei lá, o ed e lorraine, só que com menos drama e demonios. eu acho.",
                    f"feito, {nome_autor}! '{nome_filme_formatado}' foi devidamente catalogado na nossa estante virtual. espero que a crítica bianca precinotto aprove.",
                    f"registrado, {nome_autor}. a gente agora tem uma entrada nova no diário de bordo sobre '{nome_filme_formatado}'. também vou assistir depois e conto pra vocês se gostei. tomara que seja um clássico cult."
                ]
                await ctx.send(random.choice(respostas))
        except ValueError:
            await ctx.send(f"hm, {ctx.author.display_name}, essa nota aí tá esquisita. `nota:` precisa ser um número (pode usar ponto ou vírgula, tipo 6.5 ou 6,5).")
        except Exception as e:
            print(f"Ocorreu um erro no !assistido: {e}")
            await ctx.send("deu um bug geral na matrix.")

async def setup(bot):
    await bot.add_cog(Catalogo(bot))
