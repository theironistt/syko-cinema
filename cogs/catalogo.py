# cogs/catalogo.py
import discord
from discord.ext import commands
import random
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from utils import assistidos_db, watchlist_db, configuracoes_db, normalizar_texto, sanitizar_nome, parse_args

class Catalogo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def criar_embed_filme(self, filme, guild):
        embed = discord.Embed(color=discord.Color.from_rgb(255, 105, 180))
        try:
            membro = await guild.fetch_member(int(filme['escolhido_por']))
            nome_escolha = membro.display_name
        except:
            nome_escolha = str(filme.get('escolhido_por', 'N/A'))

        nome = filme.get('nome', 'Nome não encontrado')
        emojis = filme.get('emoji', '')
        ano = filme.get('ano', '')
        header_filme = f"### {nome} {emojis}"
        if ano: header_filme += f" ({ano})"

        desc = f"{header_filme}\n**Quem escolheu:** {nome_escolha}\n**Gênero:** {filme.get('genero', 'N/A').capitalize()}\n**Nota:** {filme.get('nota', 0)}/10 {filme.get('like', '—')}\n**Comentário:**\n> {filme.get('comentario', 'sem comentários.')}\n\n*(Assistido em {filme.get('data', 'N/A')})*\n"
        embed.description = desc
        return embed

    @commands.command(name='assistido')
    async def _assistido(self, ctx, *, argumentos_str: str):
        try:
            dados_capturados = parse_args(argumentos_str)
            nome_filme = dados_capturados.get('nome')
            if not nome_filme:
                return await ctx.send('o campo `nome` é essencial.')

            nome_filme_sanitizado = sanitizar_nome(nome_filme)
            print(f"Sanitizado: {nome_filme_sanitizado}")

            if await assistidos_db.find_one({'nome_sanitizado': nome_filme_sanitizado}):
                return await ctx.send("eita, parece que esse filme já tá na nossa lista de assistidos.")

            nota_str, genero = dados_capturados.get('nota'), dados_capturados.get('genero')
            if not nota_str or not genero:
                return await ctx.send('preciso pelo menos de `nome`, `nota` e `genero`.')

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

            try:
                await assistidos_db.insert_one(novo_filme)
            except DuplicateKeyError:
                return await ctx.send("eita, parece que esse filme já foi registrado nos assistidos.")

            resultado_remocao = await watchlist_db.delete_one({'nome_sanitizado': nome_filme_sanitizado})

            nome_autor = ctx.author.display_name
            if resultado_remocao.deleted_count > 0:
                await ctx.send(f"perfeito, {nome_autor}! '{novo_filme['nome']}' foi assistido e já risquei ele da nossa watchlist interminável.")
            else:
                respostas = [
                    f"anotado, {nome_autor}. '{novo_filme['nome']}' agora faz parte da nossa história...",
                    f"feito, {nome_autor}! '{novo_filme['nome']}' foi devidamente catalogado...",
                    f"registrado, capitão {nome_autor}. temos uma nova entrada no diário sobre '{novo_filme['nome']}'..."
                ]
                await ctx.send(random.choice(respostas))

            # Log automático
            print("Tentando buscar configuração do canal de log...")
            config = await configuracoes_db.find_one({'_id': 'config_servidor'})
            if config and 'canal_log_id' in config:
                log_channel_id = config['canal_log_id']
                print(f"Canal de log ID encontrado: {log_channel_id}")
                log_channel = self.bot.get_channel(log_channel_id)
                if log_channel:
                    print(f"Canal de log encontrado: {log_channel.name}")
                    log_embed = await self.criar_embed_filme(novo_filme, ctx.guild)
                    await log_channel.send(embed=log_embed)
                    print("Embed enviado para o canal de log.")
                else:
                    print(f"AVISO: Canal de log com ID {log_channel_id} não encontrado.")
            else:
                print("Nenhuma configuração de canal de log encontrada.")

        except ValueError:
            print(f"Erro de ValueError no !assistido: Nota inválida.")
            await ctx.send(f"hm, {ctx.author.display_name}, essa nota aí tá esquisita.")
        except Exception as e:
            print(f"Ocorreu um erro inesperado no !assistido: {e}")
            await ctx.send("deu um bug geral na matrix.")

async def setup(bot):
    await bot.add_cog(Catalogo(bot))
