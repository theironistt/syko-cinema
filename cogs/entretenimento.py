# cogs/entretenimento.py
import discord
from discord.ext import commands, tasks
import random
from utils import assistidos_db, configuracoes_db

class Entretenimento(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.critico_aleatorio.start()

    def cog_unload(self):
        self.critico_aleatorio.cancel()

    @tasks.loop(hours=2)
    async def critico_aleatorio(self):
        await self.bot.wait_until_ready()
        if random.randint(1, 4) != 1: return

        configs = await configuracoes_db.find({'canal_critico_id': {'$exists': True}}).to_list(length=None)
        if not configs: return

        filmes_ruins = await assistidos_db.find({'nota': {'$lte': 5}}).to_list(length=None)
        if not filmes_ruins: return
        
        filme_sorteado = random.choice(filmes_ruins)
        nome, nota = filme_sorteado['nome'], filme_sorteado['nota']
        respostas = [ f"lembrete aleatório de que vocês gastaram duas horas da vida de vocês assistindo a **'{nome}'** e deram nota **{nota}**. espero que tenham aprendido a lição. 💀", f"só passando pra lembrar daquela vez que vocês decidiram ver **'{nome}'** (nota **{nota}**). ainda bem que o amor de vocês é mais forte que o gosto pra filme.", f"arquivo x do syko cinema: **'{nome}'**, nota **{nota}**. um dia a gente descobre o que se passava na cabeça de vocês nesse dia. 👽", f"alerta de gosto duvidoso detectado no histórico! vocês realmente deram nota **{nota}** para **'{nome}'**? corajosos." ]
        
        for config in configs:
            critico_channel = self.bot.get_channel(config['canal_critico_id'])
            if critico_channel:
                try: await critico_channel.send(random.choice(respostas))
                except Exception as e: print(f"Não foi possível enviar mensagem do crítico para o canal {critico_channel.id}: {e}")

    @commands.command(name='testar_critico')
    @commands.is_owner()
    async def _testar_critico(self, ctx):
        await ctx.send("ok, forçando a execução do 'crítico oposto' para teste...")
        await self.critico_aleatorio.func(self)

async def setup(bot):
    await bot.add_cog(Entretenimento(bot))