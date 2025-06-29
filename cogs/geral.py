# cogs/geral.py
import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional
from utils import carregar_dados, salvar_dados, sanitizar_nome, normalizar_texto

class Geral(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='lista')
    async def _lista(self, ctx, filtro: Optional[str] = None):
        dados_db = carregar_dados()
        lista_assistidos = dados_db.get('assistidos', [])
        if not lista_assistidos: return await ctx.send("nosso catálogo tá vazio. use `!assistido` pra gente começar.")
        try:
            lista_assistidos.sort(key=lambda item: datetime.strptime(item.get('data', '01/01/1900'), '%d/%m/%Y'), reverse=True)
        except (ValueError, KeyError):
            await ctx.send("aviso: alguns itens da lista podem não estar ordenados por data devido a formatos inválidos.")

        titulo, lista_a_mostrar = "Catálogo Syko Cinema", []
        if filtro:
            filtro_norm = normalizar_texto(filtro)
            if filtro_norm == 'tudo':
                lista_a_mostrar, titulo = lista_assistidos, titulo + " (Completo)"
            else:
                lista_a_mostrar = [f for f in lista_assistidos if normalizar_texto(f.get('genero', '')) == filtro_norm]
                if not lista_a_mostrar: return await ctx.send(f"ué, parece que a gente nunca assistiu nada de `{filtro}`.")
                titulo += f" de {filtro.capitalize()}"
        else:
            lista_a_mostrar, titulo = lista_assistidos[:10], titulo + " (Últimos 10 Adicionados)"
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
            desc += item_completo
        if desc: embed.description = desc; await ctx.send(embed=embed)

    @commands.command(name='buscar')
    async def _buscar(self, ctx, *, termo_busca: str):
        termo_sanitizado = sanitizar_nome(termo_busca)
        dados_db = carregar_dados()
        res_assistidos = [f for f in dados_db.get('assistidos', []) if termo_sanitizado in sanitizar_nome(f['nome'])]
        res_watchlist = [i for i in dados_db.get('watchlist', []) if termo_sanitizado in sanitizar_nome(i['nome'])]
        if not res_assistidos and not res_watchlist: return await ctx.send(f"procurei em tudo, mas não achei nada parecido com '{termo_busca}'.")
        embed = discord.Embed(title=f"🔎 Resultados da busca por '{termo_busca}'", color=discord.Color.blue())
        desc = ""
        if res_assistidos: desc += "**Já assistimos:**\n" + "\n".join([f"- **{f['nome']}** (Nota: {f['nota']})" for f in res_assistidos])
        if res_watchlist: desc += "\n\n**Está na nossa watchlist:**\n" + "\n".join([f"- **{i['nome']}**" for i in res_watchlist])
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name='watchlist')
    async def _watchlist(self, ctx, *, argumento: Optional[str] = None):
        dados_db = carregar_dados()
        if argumento:
            nome_sanitizado = sanitizar_nome(argumento)
            if any(sanitizar_nome(i['nome']) == nome_sanitizado for i in dados_db.get('watchlist', [])): return await ctx.send("opa! esse filme já está na nossa lista pra assistir. tá com a memória ruim, hein?")
            if any(sanitizar_nome(f['nome']) == nome_sanitizado for f in dados_db.get('assistidos', [])): return await ctx.send("já vimos esse, cara. já esqueceu? então era ruim mesmo...")
            dados_db.setdefault('watchlist', []).append({'nome': argumento, 'adicionado_por': ctx.author.display_name})
            salvar_dados(dados_db)
            await ctx.send(f"anotado! '{argumento}' foi pra nossa watchlist.")
        else:
            watchlist = dados_db.get('watchlist', [])
            if not watchlist: return await ctx.send("nossa... a gente não quer assistir nada? a watchlist tá vazia. use `!watchlist nome do filme`.")
            embed = discord.Embed(title="🤔 Nossa Watchlist", color=discord.Color.from_rgb(255, 193, 7))
            embed.description = "\n".join([f"**{i+1}. {item['nome']}** (*add por: {item['adicionado_por']}*)" for i, item in enumerate(watchlist)])
            await ctx.send(embed=embed)

    @commands.command(name='top')
    async def _top(self, ctx):
        dados_db = carregar_dados()
        if len(dados_db.get('assistidos', [])) < 1: return await ctx.send("precisamos de mais filmes no catálogo pra eu poder montar um pódio!")
        lista_ordenada = sorted(dados_db['assistidos'], key=lambda item: float(item.get('nota', 0)), reverse=True)
        embed = discord.Embed(title="🏆 Nosso Top 5 Filmes & Séries", color=discord.Color.gold())
        medalhas = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, filme in enumerate(lista_ordenada[:5]):
            embed.add_field(name=f"{medalhas[i]} {filme['nome']}", value=f"**Nota: {filme['nota']}/10**", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name='remover')
    async def _remover(self, ctx, tipo_lista: str, *, nome_para_remover: str):
        try:
            tipo_lista_norm = normalizar_texto(tipo_lista)
            if tipo_lista_norm not in ['assistido', 'watchlist']: raise ValueError()
            chave_json = 'assistidos' if tipo_lista_norm == 'assistido' else 'watchlist'
            nome_limpo = nome_para_remover.strip('"')
            nome_sanitizado = sanitizar_nome(nome_limpo)
            dados_db = carregar_dados()
            lista_original = dados_db[chave_json]
            nova_lista = [item for item in lista_original if sanitizar_nome(item['nome']) != nome_sanitizado]
            if len(nova_lista) < len(lista_original):
                dados_db[chave_json] = nova_lista
                salvar_dados(dados_db)
                await ctx.send(f"pronto. '{nome_limpo}' foi removido da lista de `{tipo_lista_norm}`.")
            else: await ctx.send(f"não achei '{nome_limpo}' na lista de `{tipo_lista_norm}`.")
        except: await ctx.send('Comando inválido. Use `!remover assistido "nome"` ou `!remover watchlist "nome"`.')

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
