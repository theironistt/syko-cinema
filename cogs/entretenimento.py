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

    # --- NOVO COMANDO DE TESTE ---
    @commands.command(name='testar_critico')
    @commands.is_owner() # Apenas o dono do bot pode usar
    async def _testar_critico(self, ctx):
        """Força a execução da tarefa do crítico para fins de teste."""
        await ctx.send("Ok, forçando a execução do 'Crítico Oposto' para teste...")
        # Chama a função da tarefa diretamente
        await self.critico_aleatorio_task()


    @tasks.loop(hours=2)
    async def critico_aleatorio(self):
        # Garante que o bot está pronto antes de rodar
        await self.bot.wait_until_ready()

        # Adiciona uma chance de 1 em 4 de a mensagem ser enviada
        if random.randint(1, 4) != 1:
            print("Crítico Oposto decidiu ficar quieto desta vez.")
            return
        
        await self.critico_aleatorio_task()

    async def critico_aleatorio_task(self):
        """Lógica principal do crítico, agora separada para poder ser chamada pelo teste."""
        # Pega a configuração do canal do crítico
        config = await configuracoes_db.find_one({'_id': 'config_servidor'})
        # --- LÓGICA ATUALIZADA: Procura pelo canal específico do crítico ---
        if not config or 'canal_critico_id' not in config:
            print("Crítico Oposto não postou porque o canal do crítico não está configurado.")
            return

        critico_channel = self.bot.get_channel(config['canal_critico_id'])
        if not critico_channel:
            return

        # Busca no banco TODOS os filmes com nota 5 ou menor
        filmes_ruins = await assistidos_db.find({'nota': {'$lte': 5}}).to_list(length=None)

        if not filmes_ruins:
            print("Crítico Oposto não encontrou filmes ruins para zoar.")
            return
        
        filme_sorteado = random.choice(filmes_ruins)
        nome = filme_sorteado['nome']
        nota = filme_sorteado['nota']

        respostas = [
            f"lembrete aleatório de que vocês gastaram duas horas da vida de vocês assistindo a **'{nome}'** e deram nota **{nota}**. espero que tenham aprendido a lição. 💀",
            f"só passando pra lembrar daquela vez que vocês decidiram ver **'{nome}'** (nota **{nota}**). ainda bem que o amor de vocês é mais forte que o gosto pra filme.",
            f"arquivo X do syko cinema: **'{nome}'**, nota **{nota}**. um dia a gente descobre o que se passava na cabeça de vocês nesse dia. 👽",
            f"alerta de gosto duvidoso detectado no histórico! vocês realmente deram nota **{nota}** para **'{nome}'**? corajosos."
        ]
        
        await critico_channel.send(random.choice(respostas))

async def setup(bot):
    await bot.add_cog(Entretenimento(bot))