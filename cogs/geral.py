# cogs/geral.py
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional
import re
import asyncio
from calendar import monthrange
import pytz
import random
from utils import assistidos_db, watchlist_db, configuracoes_db, normalizar_texto, sanitizar_nome

# --- CLASSE PARA OS BOTÕES DE PAGINAÇÃO ---
class PaginacaoView(discord.ui.View):
    def __init__(self, ctx, embeds):
        super().__init__(timeout=180.0)
        self.ctx = ctx
        self.embeds = embeds
        self.pagina_atual = 0
        self.message = None
        self.update_buttons()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass 

    def update_buttons(self):
        self.children[0].disabled = self.pagina_atual == 0
        self.children[1].disabled = self.pagina_atual >= len(self.embeds) - 1

    @discord.ui.button(label="⬅️ anterior", style=discord.ButtonStyle.secondary)
    async def anterior_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("ops! só quem pediu a lista pode navegar.", ephemeral=True)
        self.pagina_atual -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.pagina_atual], view=self)

    @discord.ui.button(label="próximo ➡️", style=discord.ButtonStyle.secondary)
    async def proximo_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("ops! só quem pediu a lista pode navegar.", ephemeral=True)
        self.pagina_atual += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.pagina_atual], view=self)


class Geral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fuso_horario = pytz.timezone('America/Sao_Paulo')
    
    async def enviar_paginado(self, ctx, titulo_base, lista_de_itens, itens_por_pagina, desc_base=""):
        if not lista_de_itens:
            if "retrospectiva" in titulo_base.lower():
                return await ctx.send(f"pelo visto vocês não assistiram nada durante o período especificado. mês de detox? 🤣")
            else:
                return await ctx.send("num achei nenhum filme aqui com esses critérios, tenta de outro jeito...")
        
        paginas_de_dados = [lista_de_itens[i:i + itens_por_pagina] for i in range(0, len(lista_de_itens), itens_por_pagina)]
        total_paginas = len(paginas_de_dados)
        embeds_paginados = []
        nomes_cache = {}

        for i, pagina_de_dados in enumerate(paginas_de_dados):
            titulo = f"{titulo_base} (página {i + 1}/{total_paginas})"
            embed_description = desc_base if i == 0 else ""
            embed = discord.Embed(title=titulo, color=discord.Color.from_rgb(255, 105, 180), description=embed_description)
            
            for filme in pagina_de_dados:
                user_id_str = str(filme.get('escolhido_por'))
                nome_escolha = "N/A"
                if user_id_str in nomes_cache:
                    nome_escolha = nomes_cache[user_id_str]
                else:
                    try:
                        membro = await ctx.guild.fetch_member(int(user_id_str))
                        nome_escolha = membro.display_name
                        nomes_cache[user_id_str] = nome_escolha
                    except (ValueError, discord.NotFound, TypeError):
                        nome_escolha = user_id_str
                        nomes_cache[user_id_str] = nome_escolha

                nome, emojis, ano = filme.get('nome', 'nome não encontrado'), filme.get('emoji', ''), filme.get('ano', '')
                header_filme = f"{nome} {emojis}"
                if ano: header_filme += f" ({ano})"
                
                valor_campo = f"**gênero:** {filme.get('genero', 'n/a').capitalize()}\n**nota:** {filme.get('nota', 0)}/10 {filme.get('like', '—')}\n**comentário:**\n> {filme.get('comentario', 'sem comentários.')}\n*(assistido em {filme.get('data', 'n/a')})*"
                embed.add_field(name=f"🎬 {header_filme}", value=valor_campo, inline=False)
            embeds_paginados.append(embed)

        if not embeds_paginados: return
        
        view = PaginacaoView(ctx, embeds_paginados)
        view.message = await ctx.send(embed=view.embeds[0], view=view)

    @commands.command(name='configurar')
    @commands.has_permissions(administrator=True)
    async def _configurar(self, ctx, subcomando: str):
        subcomando_norm = normalizar_texto(subcomando)
        
        # --- CORREÇÃO AQUI ---
        # Trocamos o segundo 'if' por 'elif' para criar um fluxo de decisão único.
        # Agora, ele só entrará no 'else' se nenhuma das condições anteriores for verdadeira.
        if subcomando_norm == 'log_filmes':
            await configuracoes_db.update_one(
                {'_id': 'config_servidor'},
                {'$set': {'canal_log_id': ctx.channel.id}},
                upsert=True
            )
            await ctx.send(f"beleza! este canal (`#{ctx.channel.name}`) foi configurado como o diário oficial de filmes.")
        
        elif subcomando_norm == 'critico':
            await configuracoes_db.update_one(
                {'_id': 'config_servidor'},
                {'$set': {'canal_critico_id': ctx.channel.id}},
                upsert=True
            )
            await ctx.send(f"entendido. as minhas críticas ácidas e aleatórias serão enviadas aqui em `#{ctx.channel.name}`. preparem-se.")
            
        else:
            await ctx.send("hm, não conheço essa configuração. use `!configurar log_filmes` ou `!configurar critico`.")

    @commands.command(name='mes')
    async def _mes(self, ctx, *, mes_ano: str):
        mapa_meses = {'jan': 1,'janeiro': 1,'fev': 2,'fevereiro': 2,'mar': 3,'marco': 3,'março': 3,'abr': 4,'abril': 4,'mai': 5,'maio': 5,'jun': 6,'junho': 6,'jul': 7,'julho': 7,'ago': 8,'agosto': 8,'set': 9,'setembro': 9,'out': 10,'outubro': 10,'nov': 11,'novembro': 11,'dez': 12,'dezembro': 12}
        match = re.match(r'([a-zA-Z]+)\s*(\d{2,4})', mes_ano)
        if not match: return await ctx.send("formato inválido. tente `!mes junho25`.")
        
        nome_mes, ano_str = match.groups()
        mes = mapa_meses.get(normalizar_texto(nome_mes))
        ano = int(ano_str)
        if len(ano_str) == 2: ano += 2000
        if not mes: return await ctx.send(f"não reconheci o mês '{nome_mes}'.")

        primeiro_dia = self.fuso_horario.localize(datetime(ano, mes, 1))
        ultimo_dia_mes = monthrange(ano, mes)[1]
        ultimo_dia = self.fuso_horario.localize(datetime(ano, mes, ultimo_dia_mes, 23, 59, 59))
        
        query = {'data_obj': {'$gte': primeiro_dia, '$lte': ultimo_dia}}
        filmes_do_mes = await assistidos_db.find(query).sort("data_obj", -1).to_list(length=None)
        
        titulo = f"retrospectiva de {nome_mes.capitalize()} de {ano} 🍿"
        desc_base = f"em {nome_mes.capitalize()} vocês foram bem ocupados! assistiram a **{len(filmes_do_mes)}** produções." if filmes_do_mes else ""
        await self.enviar_paginado(ctx, titulo, filmes_do_mes, 5, desc_base)

    @commands.command(name='lista')
    async def _lista(self, ctx, *, filtro: Optional[str] = None):
        query, titulo = {}, "catálogo syko cinema"
        if filtro and filtro.lower() != 'tudo':
            query = {'genero': {'$regex': filtro, '$options': 'i'}}
            titulo += f" de {filtro.capitalize()}"
        
        lista_completa = await assistidos_db.find(query).to_list(length=None)
        if not lista_completa:
            if filtro: return await ctx.send(f"ué, parece que a gente nunca assistiu nada de `{filtro}`.")
            else: return await ctx.send("nosso catálogo tá vazio. use `!assistido` pra gente começar.")
        
        def get_date_obj(item):
            data_str = item.get('data', '')
            if not data_str: return datetime.min
            try: return datetime.strptime(data_str, '%d/%m/%Y')
            except ValueError:
                try: return datetime.strptime(data_str, '%d/%m/%y')
                except ValueError: return datetime.min
        lista_completa.sort(key=get_date_obj, reverse=True)
        
        lista_a_mostrar = lista_completa
        if not filtro:
            titulo += " (últimos 10 adicionados)"
            lista_a_mostrar = lista_completa[:10]
        elif filtro.lower() == 'tudo':
            titulo += " (completo)"
        
        await self.enviar_paginado(ctx, titulo, lista_a_mostrar, 3)

    @commands.command(name='buscar')
    async def _buscar(self, ctx, *, termo_busca: str):
        termo_sanitizado = sanitizar_nome(termo_busca)
        regex_query = {'$regex': '.*' + '.*'.join(termo_sanitizado.split()) + '.*', '$options': 'i'}
        res_assistidos = await assistidos_db.find({'nome_sanitizado': regex_query}).to_list(length=None)
        res_watchlist = await watchlist_db.find({'nome_sanitizado': regex_query}).to_list(length=None)
        if not res_assistidos and not res_watchlist: return await ctx.send(f"procurei em tudo, mas não achei nada parecido com '{termo_busca}'.")
        embed = discord.Embed(title=f"🔎 resultados da busca por '{termo_busca}'", color=discord.Color.blue())
        desc = ""
        if res_assistidos: desc += "**já assistimos:**\n" + "\n".join([f"- **{f['nome']}** (nota: {f['nota']})" for f in res_assistidos])
        if res_watchlist: desc += "\n\n**está na nossa watchlist:**\n" + "\n".join([f"- **{i['nome']}**" for i in res_watchlist])
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name='watchlist')
    async def _watchlist(self, ctx, *, argumento: Optional[str] = None):
        if argumento:
            nome_sanitizado = sanitizar_nome(argumento)
            if await watchlist_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("opa! esse filme já está na nossa lista pra assistir. tá com a memória ruim, hein?")
            if await assistidos_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("já vimos esse, cara. já esqueceu? então era ruim mesmo...")
            await watchlist_db.insert_one({'nome': argumento, 'nome_sanitizado': nome_sanitizado, 'adicionado_por': ctx.author.display_name})
            await ctx.send(f"anotado! '{argumento}' foi pra nossa watchlist.")
        else:
            watchlist = await watchlist_db.find().to_list(length=None)
            if not watchlist: return await ctx.send("nossa... a gente não quer assistir nada? a watchlist tá vazia.")
            embed = discord.Embed(title="🎥 nossa watchlist", color=discord.Color.from_rgb(255, 193, 7))
            embed.description = "\n".join([f"**{i+1}. {item['nome']}** (*add por: {item['adicionado_por']}*)" for i, item in enumerate(watchlist)])
            await ctx.send(embed=embed)

    @commands.command(name='top')
    async def _top(self, ctx):
        lista_ordenada = await assistidos_db.find({}).sort("nota", -1).limit(5).to_list(length=5)
        if not lista_ordenada: return await ctx.send("precisamos de pelo menos um filme no catálogo pra eu poder montar um pódio!")
        embed = discord.Embed(title="🏆 nosso top 5 filmes & séries", color=discord.Color.gold())
        medalhas = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, filme in enumerate(lista_ordenada):
            embed.add_field(name=f"{medalhas[i]} {filme['nome']}", value=f"**nota: {filme['nota']}/10**", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name='remover')
    async def _remover(self, ctx, tipo_lista: str, *, nome_para_remover: str):
        try:
            tipo_lista_norm = normalizar_texto(tipo_lista)
            if tipo_lista_norm not in ['assistido', 'watchlist']: raise ValueError()
            collection = assistidos_db if tipo_lista_norm == 'assistido' else watchlist_db
            nome_limpo = nome_para_remover.strip('"')
            resultado = await collection.delete_one({'nome_sanitizado': sanitizar_nome(nome_limpo)})
            if resultado.deleted_count > 0: await ctx.send(f"prontin man. '{nome_limpo}' foi removido da lista de `{tipo_lista_norm}`.")
            else: await ctx.send(f"não achei '{nome_limpo}' na lista de `{tipo_lista_norm}`.")
        except: await ctx.send('comando inválido. use `!remover assistido "nome"` ou `!remover watchlist "nome"`.')

    @commands.command(name='comandos')
    async def _comandos(self, ctx):
        embed = discord.Embed(title="📜 lista de comandos do syko cinema", color=discord.Color.dark_green(), description="eu entendo os campos mesmo sem acento ou ':' (dois-pontos)!")
        embed.add_field(name="`!assistido`", value="`nome [nome] nota [nota] genero [genero]`\n*opcionais: `liked sim`, `comentario [texto]`, `escolhido por [nome]`, `data [d/m/a]`, `ano [ano]`, `emoji [emojis]`*", inline=False)
        embed.add_field(name="`!configurar log_filmes`", value="define o canal atual para postar as notas de filmes.", inline=False)
        embed.add_field(name="`!configurar critico`", value="define o canal atual para as zoeiras do crítico oposto.", inline=False)
        embed.add_field(name="`!agendar`", value="`nome [nome] data [d/m/a] hora [h:m]`", inline=False)
        embed.add_field(name="`!agenda`", value="mostra as próximas sessões agendadas.", inline=False)
        embed.add_field(name="`!cancelar \"[nome]\"`", value="cancela uma sessão agendada.", inline=False)
        embed.add_field(name="`!remover assistido \"[nome]\"`", value="remove um filme do histórico.", inline=False)
        embed.add_field(name="`!remover watchlist \"[nome]\"`", value="remove um filme da watchlist.", inline=False)
        embed.add_field(name="`!lista`, `!lista [genero]`, `!lista tudo`", value="mostra os filmes assistidos.", inline=False)
        embed.add_field(name="`!buscar [termo]`", value="busca por um filme em todas as listas.", inline=False)
        embed.add_field(name="`!watchlist [nome]` / `!watchlist`", value="adiciona um filme à watchlist ou a lista.", inline=False)
        embed.add_field(name="`!top`", value="exibe o ranking dos 5 melhores.", inline=False)
        embed.add_field(name="`!placar`", value="mostra o placar de quem escolheu os melhores filmes.", inline=False)
        embed.add_field(name="`!testar_critico`", value="*(apenas para o dono do bot) força uma aparição do crítico oposto.*", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name='placar')
    async def _placar(self, ctx):
        filmes = await assistidos_db.find({}).to_list(length=None)
        if not filmes: return await ctx.send("vocês ainda não assistiram nada juntos 😿 use `!assistido` pra começar esse romance cinematográfico.")
        placar = {}
        for filme in filmes:
            autor = filme.get('escolhido_por')
            if not autor: continue
            if autor not in placar: placar[autor] = {'nome': str(autor), 'quantidade': 0, 'soma_notas': 0.0, 'likes': 0}
            placar[autor]['quantidade'] += 1
            placar[autor]['soma_notas'] += float(filme.get('nota', 0))
            if filme.get('like') == '🌟': placar[autor]['likes'] += 1
        if not placar: return await ctx.send("ué... ninguém escolheu nada? isso é uma democracia cinematográfica suspensa 🎬🗳️")
        for user_id in list(placar.keys()):
            try: placar[user_id]['nome'] = (await ctx.guild.fetch_member(int(user_id))).display_name
            except: pass
        ranking = []
        for user_id, stats in placar.items():
            media = stats['soma_notas'] / stats['quantidade'] if stats['quantidade'] > 0 else 0
            ranking.append({'nome': stats['nome'], 'quantidade': stats['quantidade'], 'media': media, 'likes': stats['likes']})
        ranking.sort(key=lambda x: (x['media'], x['likes']), reverse=True)
        msg = "📊 eu sou o verdadeiro vencedor, que tive que assistir vocês dois calado. mas tá aqui o ranking: \n"
        medalhas = ["🥇", "🥈", "🥉"]
        for i, pessoa in enumerate(ranking):
            medalha = medalhas[i] if i < len(medalhas) else f"{i+1}."
            msg += f"\n{medalha} **{pessoa['nome']}**\n- {pessoa['quantidade']} filme(s) escolhidos\n- média: {pessoa['media']:.2f}\n- {pessoa['likes']} ganharam like supremo 🌟\n"
        msg += "\ne o prêmio é vocês terem se achado mesmo com esse gosto esquisito. parabéns! 🎥💔🫶"
        await ctx.send(msg)



async def setup(bot):
    await bot.add_cog(Geral(bot))