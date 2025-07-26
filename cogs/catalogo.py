# cogs/catalogo.py
import discord
from discord.ext import commands
import random
from datetime import datetime
from utils import assistidos_db, watchlist_db, configuracoes_db, normalizar_texto, sanitizar_nome, parse_args
from pymongo.errors import DuplicateKeyError

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
        nome, emojis, ano = filme['nome'], filme.get('emoji', ''), filme.get('ano', '')
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
                return await ctx.send('tá faltando o nome. dãaaa.')

            nome_filme_sanitizado = sanitizar_nome(nome_filme)
            
            if await assistidos_db.find_one({'nome_sanitizado': nome_filme_sanitizado}):
                return await ctx.send("eita, esse filme já tá nos nossos assistidos. se não lembra é pq era ruim, né.")

            nota_str, genero = dados_capturados.get('nota'), dados_capturados.get('genero')
            if not nota_str or not genero:
                return await ctx.send('perai, zé ruela. preciso pelo menos de `nome:`, `nota:` e `genero:`. escreve direito, eu to fazendo a maior parte')

            data_str = dados_capturados.get('data', datetime.now().strftime('%d/%m/%Y'))
            try:
                formato_data = '%d/%m/%Y' if len(data_str.split('/')[-1]) == 4 else '%d/%m/%y'
                data_obj = datetime.strptime(data_str, formato_data)
            except ValueError:
                return await ctx.send("O formato da data parece inválido. Use `dd/mm/aaaa` ou `dd/mm/aa`.")

            novo_filme = {
                'nome': nome_filme.strip(), 'nome_sanitizado': nome_filme_sanitizado,
                'nota': float(nota_str.replace(',', '.')),
                'like': '🌟' if dados_capturados.get('liked', '').lower() == 'sim' else '—',
                'genero': genero, 'comentario': dados_capturados.get('comentario', 'sem comentários.'),
                'data': data_obj.strftime('%d/%m/%Y'), 'data_obj': data_obj,
                'ano': dados_capturados.get('ano', ''), 'emoji': dados_capturados.get('emoji', ''),
                'adicionado_por': ctx.author.id
            }

            escolhido_por_str = dados_capturados.get('escolhido por')
            if escolhido_por_str:
                membro = discord.utils.find(lambda m: normalizar_texto(m.display_name).startswith(normalizar_texto(escolhido_por_str)), ctx.guild.members)
                novo_filme['escolhido_por'] = membro.id if membro else escolhido_por_str
            else:
                novo_filme['escolhido_por'] = ctx.author.id

            await assistidos_db.insert_one(novo_filme)
            
            resultado_remocao = await watchlist_db.delete_one({'nome_sanitizado': nome_filme_sanitizado})
            
            nome_autor = ctx.author.display_name
            if resultado_remocao.deleted_count > 0:
                await ctx.send(f"perfeito, {nome_autor}! '{novo_filme['nome']}' foi assistido e já risquei ele da nossa watchlist interminável.")
            else:
                nota = novo_filme['nota']
                nome_filme_formatado = novo_filme['nome']
                if nota >= 9:
                    respostas = [ f"'{nome_filme_formatado}' foi catalogado com sucesso, {nome_autor}... e com essa nota, deve ter sido bão mesmo! vou assistir. 🌟🎬", f"anotado. '{nome_filme_formatado}' faz parte do culto agora já que a nota foi boa", f"pronto, {nome_autor}. '{nome_filme_formatado}' tá na lista e no seu coração pelo visto, né? o trem foi bom aí com essa nota", f"nota {nota}? certeza que não foi dopado por efeitos especiais ou trilha emocional? 🤔", f"anotei aqui..nota {nota}.. bom saber que tao so assistindo filmes bons e nada de comprar sachezinho bom pra mim tb" ]
                elif 6 <= nota < 9:
                    respostas = [ f"'{nome_filme_formatado}' entrou na lista, {nome_autor}. parece que agradou... mas não o suficiente pra eu assistir também 🎞️", f"ok, '{nome_filme_formatado}' catalogado. nota média, gosto ok. nada revolucionário, nada cancelável. 🫱🫲", f"foi, {nome_autor}. '{nome_filme_formatado}' tá salvo e foi digno de um 'hm, bom'. foi igual pizza fria: não impressiona, mas alimenta 🍕", f"registrado. nota segura. vai valer o comentário no letterboxd?" ]
                else:
                    respostas = [ f"ok, '{nome_filme_formatado}' registrado, mas {nota}/10? alguém se arrependeu da escolha 🫢", f"pronto, {nome_autor}. '{nome_filme_formatado}' tá na lista, mas confessa: você só viu até o final por teimosia mesmo 😬", f"feito. nota baixa e nenhum like? isso parece castigo e não entretenimento 📉📼", f"ok. '{nome_filme_formatado}' foi adicionado, mas vou fingir que você não viu isso sóbrio 👀" ]
                await ctx.send(random.choice(respostas))

            config = await configuracoes_db.find_one({'_id': ctx.guild.id})
            if config and 'canal_log_id' in config:
                log_channel = self.bot.get_channel(config['canal_log_id'])
                if log_channel:
                    try:
                        log_embed = await self.criar_embed_filme(novo_filme, ctx.guild)
                        await log_channel.send(embed=log_embed)
                    except Exception as log_error: print(f"Erro ao postar no canal de log: {log_error}")

        except ValueError:
            await ctx.send(f"hm, {ctx.author.display_name}, essa nota aí tá esquisita.")
        except Exception as e:
            print(f"Ocorreu um erro no !assistido: {e}")
            await ctx.send("peraí, neo...deu um bug geral na matrix.")

async def setup(bot):
    await bot.add_cog(Catalogo(bot))