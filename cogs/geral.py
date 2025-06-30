# cogs/geral.py
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional
from utils import assistidos_db, watchlist_db, configuracoes_db, normalizar_texto, sanitizar_nome

class Geral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='configurar')
    @commands.has_permissions(administrator=True) # Apenas administradores podem usar
    async def _configurar(self, ctx, subcomando: str):
        if normalizar_texto(subcomando) == 'canal_log':
            await configuracoes_db.update_one(
                {'_id': 'config_servidor'},
                {'$set': {'canal_log_id': ctx.channel.id}},
                upsert=True
            )
            await ctx.send(f"beleza! este canal (`#{ctx.channel.name}`) foi configurado como o diário oficial de filmes.")
        else:
            await ctx.send("hm, não conheço essa configuração. por enquanto, só sei `!configurar canal_log`.")

    @commands.command(name='lista')
    async def _lista(self, ctx, *, filtro: Optional[str] = None):
        query = {}
        titulo = "Catálogo Syko Cinema"
        
        if filtro and filtro.lower() != 'tudo':
            query = {'genero': {'$regex': filtro, '$options': 'i'}}
            titulo += f" de {filtro.capitalize()}"

        cursor = assistidos_db.find(query)
        lista_completa = await cursor.to_list(length=None)
        
        if not lista_completa:
            if filtro: return await ctx.send(f"ué, parece que a gente nunca assistiu nada de `{filtro}`.")
            else: return await ctx.send("nosso catálogo tá vazio. use `!assistido` pra gente começar.")

        # --- CORREÇÃO FINAL: Lógica de ordenação que entende 2 e 4 dígitos ---
        def get_date_obj(item):
            data_str = item.get('data', '')
            if not data_str:
                return datetime.min # Se não houver data, vai para o final

            try:
                # Tenta primeiro o formato com 4 dígitos no ano
                return datetime.strptime(data_str, '%d/%m/%Y')
            except ValueError:
                try:
                    # Se falhar, tenta o formato com 2 dígitos no ano
                    return datetime.strptime(data_str, '%d/%m/%y')
                except ValueError:
                    # Se ambos falharem, vai para o final
                    return datetime.min

        lista_completa.sort(key=get_date_obj, reverse=True)
        
        lista_a_mostrar = []
        if filtro and filtro.lower() == 'tudo':
            lista_a_mostrar = lista_completa
            titulo += " (Completo)"
        elif not filtro:
            lista_a_mostrar = lista_completa[:10]
            titulo += " (Últimos 10 Adicionados)"
        else:
            lista_a_mostrar = lista_completa

        if not lista_a_mostrar:
            return
            
        embed = discord.Embed(title=titulo, color=discord.Color.from_rgb(255, 105, 180))
        desc = ""
        for filme in lista_a_mostrar:
            try: nome_escolha = (await ctx.guild.fetch_member(int(filme['escolhido_por']))).display_name
            except: nome_escolha = str(filme.get('escolhido_por', 'N/A'))
            
            nome = filme.get('nome', 'Nome não encontrado')
            emojis = filme.get('emoji', '')
            ano = filme.get('ano', '')
            header_filme = f"### {nome} {emojis}"
            if ano: header_filme += f" ({ano})"
            
            item_completo = f"\n---\n{header_filme}\n**Quem escolheu:** {nome_escolha}\n**Gênero:** {filme.get('genero', 'N/A').capitalize()}\n**Nota:** {filme.get('nota', 0)}/10 {filme.get('like', '—')}\n**Comentário:**\n> {filme.get('comentario', 'sem comentários.')}\n\n*(Assistido em {filme.get('data', 'N/A')})*\n"
            
            if len(desc) + len(item_completo) > 4000:
                embed.description = desc
                await ctx.send(embed=embed)
                desc = ""
                embed = discord.Embed(color=discord.Color.from_rgb(255, 105, 180))

            desc += item_completo
        
        if desc:
            embed.description = desc
            await ctx.send(embed=embed)

    @commands.command(name='buscar')
    async def _buscar(self, ctx, *, termo_busca: str):
        termo_sanitizado = sanitizar_nome(termo_busca)
        regex_query = {'$regex': '.*' + '.*'.join(termo_sanitizado.split()) + '.*', '$options': 'i'}
        res_assistidos = await assistidos_db.find({'nome_sanitizado': regex_query}).to_list(length=None)
        res_watchlist = await watchlist_db.find({'nome_sanitizado': regex_query}).to_list(length=None)
        if not res_assistidos and not res_watchlist: return await ctx.send(f"procurei em tudo, mas não achei nada parecido com '{termo_busca}'.")
        embed = discord.Embed(title=f"🔎 Resultados da busca por '{termo_busca}'", color=discord.Color.blue())
        desc = ""
        if res_assistidos: desc += "**Já assistimos:**\n" + "\n".join([f"- **{f['nome']}** (Nota: {f['nota']})" for f in res_assistidos])
        if res_watchlist: desc += "\n\n**Está na nossa watchlist:**\n" + "\n".join([f"- **{i['nome']}**" for i in res_watchlist])
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name='watchlist')
    async def _watchlist(self, ctx, *, argumento: Optional[str] = None):
        if argumento:
            nome_sanitizado = sanitizar_nome(argumento)
            if await watchlist_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("opa! esse filme já está na nossa lista pra assistir.")
            if await assistidos_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("já vimos esse, cara. já esqueceu?")
            await watchlist_db.insert_one({'nome': argumento, 'nome_sanitizado': nome_sanitizado, 'adicionado_por': ctx.author.display_name})
            await ctx.send(f"anotado! '{argumento}' foi pra nossa watchlist.")
        else:
            watchlist = await watchlist_db.find().to_list(length=None)
            if not watchlist: return await ctx.send("nossa... a gente não quer assistir nada? a watchlist tá vazia.")
            embed = discord.Embed(title="🤔 Nossa Watchlist", color=discord.Color.from_rgb(255, 193, 7))
            embed.description = "\n".join([f"**{i+1}. {item['nome']}** (*add por: {item['adicionado_por']}*)" for i, item in enumerate(watchlist)])
            await ctx.send(embed=embed)

    @commands.command(name='top')
    async def _top(self, ctx):
        lista_ordenada = await assistidos_db.find({}).sort("nota", -1).limit(5).to_list(length=5)
        if not lista_ordenada: return await ctx.send("precisamos de pelo menos um filme no catálogo para eu poder montar um pódio!")
        embed = discord.Embed(title="🏆 Nosso Top 5 Filmes & Séries", color=discord.Color.gold())
        medalhas = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, filme in enumerate(lista_ordenada):
            embed.add_field(name=f"{medalhas[i]} {filme['nome']}", value=f"**Nota: {filme['nota']}/10**", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name='remover')
    async def _remover(self, ctx, tipo_lista: str, *, nome_para_remover: str):
        try:
            tipo_lista_norm = normalizar_texto(tipo_lista)
            if tipo_lista_norm not in ['assistido', 'watchlist']: raise ValueError()
            collection = assistidos_db if tipo_lista_norm == 'assistido' else watchlist_db
            nome_limpo = nome_para_remover.strip('"')
            resultado = await collection.delete_one({'nome_sanitizado': sanitizar_nome(nome_limpo)})
            if resultado.deleted_count > 0: await ctx.send(f"pronto. '{nome_limpo}' foi removido da lista de `{tipo_lista_norm}`.")
            else: await ctx.send(f"não achei '{nome_limpo}' na lista de `{tipo_lista_norm}`.")
        except: await ctx.send('Comando inválido. Use `!remover assistido "nome"` ou `!remover watchlist "nome"`.')

    @commands.command(name='comandos')
    async def _comandos(self, ctx):
        embed = discord.Embed(title="📜 Lista de Comandos do Syko Cinema", color=discord.Color.dark_green(), description="Eu entendo os campos mesmo sem acento ou ':' (dois-pontos)!")
        embed.add_field(name="`!assistido`", value="`nome [nome] nota [nota] genero [genero]`\n*Opcionais: `liked sim`, `comentario [texto]`, `escolhido por [nome]`, `data [d/m/a]`, `ano [ano]`, `emoji [emojis]`*", inline=False)
        embed.add_field(name="`!configurar canal_log`", value="Use no canal onde você quer que as novas entradas sejam postadas.", inline=False)
        embed.add_field(name="`!remover assistido \"[nome]\"`", value="Remove um filme do histórico.", inline=False)
        embed.add_field(name="`!lista`, `!lista [genero]`, `!lista tudo`", value="Mostra os filmes assistidos.", inline=False)
        embed.add_field(name="`!buscar [termo]`", value="Busca por um filme em todas as listas.", inline=False)
        embed.add_field(name="`!watchlist [nome]` / `!watchlist`", value="Adiciona um filme à watchlist ou a lista.", inline=False)
        embed.add_field(name="`!top`", value="Exibe o ranking dos 5 melhores.", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name='placar')
    async def _placar(self, ctx):
        filmes = await assistidos_db.find({}).to_list(length=None)
        if not filmes:
            return await ctx.send("ain... vocês ainda não assistiram nada juntos 😿 use `!assistido` pra começar esse romance cinematográfico.")

        placar = {}
        for filme in filmes:
            autor = filme.get('escolhido_por')
            if not autor:
                continue
            if autor not in placar:
                placar[autor] = {'nome': str(autor), 'quantidade': 0, 'soma_notas': 0.0, 'likes': 0}
            placar[autor]['quantidade'] += 1
            placar[autor]['soma_notas'] += float(filme.get('nota', 0))
            if filme.get('like') == '🌟':
                placar[autor]['likes'] += 1

        if not placar:
            return await ctx.send("ué... ninguém escolheu nada? isso é uma democracia cinematográfica suspensa 🎬🗳️")

        # tenta pegar os nomes reais
        for user_id in placar:
            try:
                membro = await ctx.guild.fetch_member(int(user_id))
                placar[user_id]['nome'] = membro.display_name
            except:
                pass

        # calcula média e prepara lista para ordenação
        ranking = []
        for user_id, stats in placar.items():
            media = stats['soma_notas'] / stats['quantidade']
            ranking.append({
                'nome': stats['nome'],
                'quantidade': stats['quantidade'],
                'media': media,
                'likes': stats['likes']
            })

        # ordena por média, depois por likes
        ranking.sort(key=lambda x: (x['media'], x['likes']), reverse=True)

        # mensagem sarcástica
        msg = "📊 eu sou o verdadeiro vencedor, que tive que assistir vocês dois calado. mas tá aqui o ranking: \n"
        medalhas = ["🥇", "🥈", "🥉"]

        for i, pessoa in enumerate(ranking):
            medalha = medalhas[i] if i < len(medalhas) else f"{i+1}."
            nome = pessoa['nome']
            qtd = pessoa['quantidade']
            media = pessoa['media']
            likes = pessoa['likes']
            msg += f"\n{medalha} **{nome}**\n"
            msg += f"- {qtd} filme(s) escolhidos\n"
            msg += f"- média: {media:.2f}\n"
            msg += f"- {likes} ganharam like supremo 🌟\n"

        msg += "\ne o prêmio é vocês terem se achado mesmo com esse gosto esquisito. parabéns! 🎥💔🫶"

        await ctx.send(msg)



async def setup(bot):
    await bot.add_cog(Geral(bot))