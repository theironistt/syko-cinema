# cogs/agenda.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import pytz # <-- Importa a nova biblioteca de fuso horário
from utils import carregar_dados, salvar_dados, sanitizar_nome, parse_args

class Agenda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # --- CORREÇÃO: Define nosso fuso horário ---
        self.fuso_horario = pytz.timezone('America/Sao_Paulo')
        self.verificar_agendamentos.start()

    @tasks.loop(seconds=60)
    async def verificar_agendamentos(self):
        await self.bot.wait_until_ready()
        dados_db = carregar_dados()
        # --- CORREÇÃO: Pega a hora atual JÁ com o fuso horário correto ---
        agora = datetime.now(self.fuso_horario)

        agendamentos_modificados = False
        for agendamento in list(dados_db.get('agendamentos', [])):
            data_agendamento = datetime.fromisoformat(agendamento['data_iso'])
            canal = self.bot.get_channel(agendamento['canal_id'])
            if not canal: continue

            if agora >= data_agendamento:
                msg = f"🍿 **HORA DO FILME!** 🍿\nPreparem a pipoca que a sessão de **'{agendamento['filme']}'** começa agora!"
                await canal.send(msg)
                dados_db['agendamentos'].remove(agendamento)
                agendamentos_modificados = True

            elif data_agendamento - timedelta(minutes=15) <= agora and '15min' not in agendamento['lembretes_enviados']:
                msg = f"📣 **QUASE NA HORA!** Faltam só 15 minutinhos para a nossa sessão de **'{agendamento['filme']}'**. Vão pegando o cobertor!"
                await canal.send(msg)
                agendamento['lembretes_enviados'].append('15min')
                agendamentos_modificados = True

            elif data_agendamento.date() == agora.date() and agora.hour < data_agendamento.hour and 'diario' not in agendamento['lembretes_enviados']:
                hora_formatada = data_agendamento.strftime('%H:%M')
                msg = f"✨ **LEMBRETE DO DIA:** Não esqueçam que hoje tem sessão de **'{agendamento['filme']}'** às {hora_formatada}! ✨"
                await canal.send(msg)
                agendamento['lembretes_enviados'].append('diario')
                agendamentos_modificados = True

        if agendamentos_modificados:
            salvar_dados(dados_db)

    async def cog_unload(self):
        self.verificar_agendamentos.cancel()

    @commands.command(name='agendar')
    async def _agendar(self, ctx, *, args: str):
        try:
            dados_capturados = parse_args(args)
            nome_filme = dados_capturados.get('nome')
            data_str = dados_capturados.get('data')
            hora_str = dados_capturados.get('hora')

            if not nome_filme or not data_str or not hora_str:
                return await ctx.send('formato inválido. use: `!agendar nome "filme" data [d/m/a] hora [h:m]`')

            formato_data = '%d/%m/%Y' if len(data_str.split('/')[-1]) == 4 else '%d/%m/%y'
            # Cria a data "ingênua" primeiro
            data_hora_sem_fuso = datetime.strptime(f"{data_str} {hora_str}", f'{formato_data} %H:%M')
            # --- CORREÇÃO: Aplica o fuso horário à data que você digitou ---
            data_hora_agendamento = self.fuso_horario.localize(data_hora_sem_fuso)

            # --- CORREÇÃO: Compara com a hora atual, também com fuso horário ---
            if data_hora_agendamento < datetime.now(self.fuso_horario):
                return await ctx.send("ei, viajante no tempo! não podemos agendar coisas no passado.")

            dados_db = carregar_dados()
            novo_agendamento = {'filme': nome_filme, 'data_iso': data_hora_agendamento.isoformat(), 'canal_id': ctx.channel.id, 'lembretes_enviados': []}
            dados_db.setdefault('agendamentos', []).append(novo_agendamento)
            salvar_dados(dados_db)

            await ctx.send(f"boa! sessão de **'{nome_filme}'** agendada para {data_str} às {hora_str}. eu vou lembrar vocês, prometo.")
        except Exception as e:
            print(f"Erro no !agendar: {e}")
            await ctx.send("algo deu errado no agendamento. verifique o formato da data e hora.")

    @commands.command(name='agenda')
    async def _agenda(self, ctx):
        dados_db = carregar_dados()
        agendamentos = sorted(dados_db.get('agendamentos', []), key=lambda x: x['data_iso'])
        if not agendamentos: return await ctx.send("não temos nenhuma sessão de cinema marcada. `!agendar`?")
        embed = discord.Embed(title="🗓️ Próximas Sessões Agendadas", color=discord.Color.teal())
        desc = ""
        for agendamento in agendamentos:
            data_hora_utc = datetime.fromisoformat(agendamento['data_iso'])
            # Converte a data salva para o nosso fuso horário na hora de mostrar
            data_hora_local = data_hora_utc.astimezone(self.fuso_horario)
            desc += f"**🎬 {agendamento['filme']}**\n- **Quando:** {data_hora_local.strftime('%d/%m/%Y às %H:%M')}\n"
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name='cancelar')
    async def _cancelar(self, ctx, *, nome_para_cancelar: str):
        nome_limpo = nome_para_cancelar.strip('"')
        nome_sanitizado = sanitizar_nome(nome_limpo)
        dados_db = carregar_dados()
        agendamentos = dados_db.get('agendamentos', [])
        nova_lista = [ag for ag in agendamentos if sanitizar_nome(ag['filme']) != nome_sanitizado]

        if len(nova_lista) < len(agendamentos):
            dados_db['agendamentos'] = nova_lista
            salvar_dados(dados_db)
            await ctx.send(f"agendamento de '{nome_limpo}' cancelado. fica pra próxima então.")
        else: await ctx.send(f"não achei nenhum agendamento para '{nome_limpo}'.")

async def setup(bot):
    await bot.add_cog(Agenda(bot))
