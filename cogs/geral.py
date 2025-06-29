# cogs/geral.py
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional
from utils import assistidos_db, watchlist_db, normalizar_texto, sanitizar_nome

class Geral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='lista')
    async def _lista(self, ctx, *, filtro: Optional[str] = None):
        query = {}
        if filtro and filtro.lower() != 'tudo':
            query = {'genero': {'$regex': filtro, '$options': 'i'}}

        cursor = assistidos_db.find(query)
        lista_completa = await cursor.to_list(length=None)
        
        if not lista_completa:
            if filtro: return await ctx.send(f"ué, parece que a gente nunca assistiu nada de `{filtro}`.")
            else: return await ctx.send("nosso catálogo tá vazio. use `!assistido` pra gente começar.")

        lista_completa.sort(key=lambda item: datetime.strptime(item.get('data', '01/01/1900'), '%d/%m/%Y'), reverse=True)

        titulo = "Catálogo Syko Cinema"
        lista_a_mostrar = []
        if filtro and filtro.lower() == 'tudo':
            lista_a_mostrar, titulo = lista_completa, titulo + " (Completo)"
        elif filtro:
            lista_a_mostrar, titulo = lista_completa, titulo + f" de {filtro.capitalize()}"
        else:
            lista_a_mostrar, titulo = lista_completa[:10], titulo + " (Últimos 10 Adicionados)"
        
        embed = discord.Embed(title=titulo, color=discord.Color.from_rgb(255, 105, 180))
        desc = ""
        for filme in lista_a_mostrar:
            try: nome_escolha = (await ctx.guild.fetch_member(int(filme['escolhido_por']))).display_name
            except: nome_escolha = str(filme.get('escolhido_por', 'N/A'))
            
            nome, emojis, ano = filme['nome'], filme.get('emoji', ''), filme.get('ano', '')
            header_filme = f"### {nome} {emojis}"
            if ano: header_filme += f" ({ano})"
            
            item_completo = f"\n---\n{header_filme}\n**Quem escolheu:** {nome_escolha}\n**Gênero:** {filme.get('genero', 'N/A').capitalize()}\n**Nota:** {filme['nota']}/10 {filme['like']}\n**Comentário:**\n> {filme['comentario']}\n\n*(Assistido em {filme['data']})*\n"
            if len(desc) + len(item_completo) > 4000:
                embed.description = desc; await ctx.send(embed=embed); desc = ""
                embed = discord.Embed(color=discord.Color.from_rgb(255, 105, 180))
            desc += item_completo
        if desc: embed.description = desc; await ctx.send(embed=embed)

    @commands.command(name='buscar')
    async def _buscar(self, ctx, *, termo_busca: str):
        termo_sanitizado = sanitizar_nome(termo_busca)
        regex_query = {'$regex': termo_sanitizado.replace(" ", ".*"), '$options': 'i'}
        
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
            if await watchlist_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("opa! esse filme já está na nossa lista pra assistir. tá com a memória ruim, hein?")
            if await assistidos_db.find_one({'nome_sanitizado': nome_sanitizado}): return await ctx.send("já vimos esse, cara. já esqueceu? então era ruim mesmo...")
            
            await watchlist_db.insert_one({'nome': argumento, 'nome_sanitizado': nome_sanitizado, 'adicionado_por': ctx.author.display_name})
            await ctx.send(f"anotado! '{argumento}' foi pra nossa watchlist.")
        else:
            cursor = watchlist_db.find()
            watchlist = await cursor.to_list(length=None)
            if not watchlist: return await ctx.send("nossa... a gente não quer assistir nada? a watchlist tá vazia.")
            
            embed = discord.Embed(title="🤔 Nossa Watchlist", color=discord.Color.from_rgb(255, 193, 7))
            embed.description = "\n".join([f"**{i+1}. {item['nome']}** (*add por: {item['adicionado_por']}*)" for i, item in enumerate(watchlist)])
            await ctx.send(embed=embed)

    @commands.command(name='top')
    async def _top(self, ctx):
        cursor = assistidos_db.find({}).sort("nota", -1).limit(5)
        lista_ordenada = await cursor.to_list(length=5)
        if not lista_ordenada: return await ctx.send("precisamos de pelo menos um filme no catálogo pra eu poder montar um pódio!")
        
        embed = discord.Embed(title="🏆 Nosso Top 5 Filmes & Séries", color=discord.Color.gold())
        medalhas = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, filme in enumerate(lista_ordenada):
            embed.add_field(name=f"{medalhas[i]} {filme['nome']}", value=f"**Nota: {filme['nota']}/10**", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name='remover')
    async def _remover(self, ctx, tipo_lista: str, *, nome_para_remover: str):
        tipo_lista_norm = normalizar_texto(tipo_lista)
        if tipo_lista_norm not in ['assistido', 'watchlist']: return await ctx.send('Comando inválido. Use `!remover assistido "nome"` ou `!remover watchlist "nome"`.')
        
        nome_limpo = nome_para_remover.strip('"')
        collection = assistidos_db if tipo_lista_norm == 'assistido' else watchlist_db
        resultado = await collection.delete_one({'nome_sanitizado': sanitizar_nome(nome_limpo)})
        
        if resultado.deleted_count > 0:
            await ctx.send(f"pronto. '{nome_limpo}' foi removido da lista de `{tipo_lista_norm}`.")
        else: await ctx.send(f"não achei '{nome_limpo}' na lista de `{tipo_lista_norm}`.")

    @commands.command(name='comandos')
    async def _comandos(self, ctx):
        embed = discord.Embed(title="📜 Lista de Comandos do Syko Cinema", color=discord.Color.dark_green(), description="Eu entendo os campos mesmo sem acento ou ':' (dois-pontos)!")
        embed.add_field(name="`!assistido`", value="`nome [nome] nota [nota] genero [genero]`\n*Opcionais: `liked sim`, `comentario [texto]`, `escolhido por [nome]`, `data [d/m/a]`, `ano [ano]`, `emoji [emojis]`*", inline=False)
        embed.add_field(name="`!agendar`", value="`nome [nome] data [d/m/a] hora [h:m]`", inline=False)
        embed.add_field(name="`!agenda`", value="Mostra as próximas sessões agendadas.", inline=False)
        embed.add_field(name="`!cancelar \"[nome]\"`", value="Cancela uma sessão agendada.", inline=False)
        embed.add_field(name="`!remover assistido \"[nome]\"`", value="Remove um filme do histórico.", inline=False)
        embed.add_field(name="`!remover watchlist \"[nome]\"`", value="Remove um filme da watchlist.", inline=False)
        embed.add_field(name="`!lista`, `!lista [genero]`, `!lista tudo`", value="Mostra os filmes assistidos.", inline=False)
        embed.add_field(name="`!buscar [termo]`", value="Busca por um filme em todas as listas.", inline=False)
        embed.add_field(name="`!watchlist [nome]` / `!watchlist`", value="Adiciona um filme à watchlist ou a lista.", inline=False)
        embed.add_field(name="`!top`", value="Exibe o ranking dos 5 melhores.", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Geral(bot))