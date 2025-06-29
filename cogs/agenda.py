# cogs/agenda.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import pytz
from utils import agendamentos_db, parse_args, sanitizar_nome

class Agenda(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.fuso_horario = pytz.timezone('America/Sao_Paulo')
        self.verificar_agendamentos.start()

    @tasks.loop(seconds=60)
    async def verificar_agendamentos(self):
        await self.bot.wait_until_ready()
        agora = datetime.now(self.fuso_horario)
        
        cursor = agendamentos_db.find({})
        agendamentos_atuais = await cursor.to_list(length=None)

        for agendamento in agendamentos_atuais:
            data_agendamento = datetime.fromisoformat(agendamento['data_iso'])
            canal = self.bot.get_channel(agendamento['canal_id'])
            if not canal: continue

            if agora >= data_agendamento:
                msg = f"🍿 **HORA DO FILME, @here!** 🍿\nPreparem a pipoca que a sessão de **'{agendamento['filme']}'** começa agora!"
                await canal.send(msg)
                await agendamentos_db.delete_one({'_id': agendamento['_id']})
            
            elif data_agendamento - timedelta(minutes=15) <= agora and '15min' not in agendamento['lembretes_enviados']:
                msg = f"📣 **QUASE NA HORA!** Faltam só 15 minutinhos para a nossa sessão de **'{agendamento['filme']}'**. Vão pegando o cobertor!"
                await canal.send(msg)
                await agendamentos_db.update_one({'_id': agendamento['_id']}, {'$push': {'lembretes_enviados': '15min'}})

            elif data_agendamento.date() == agora.date() and agora.hour < data_agendamento.hour and 'diario' not in agendamento['lembretes_enviados']:
                hora_formatada = data_agendamento.strftime('%H:%M')
                msg = f"✨ **LEMBRETE DO DIA:** Não esqueçam que hoje tem sessão de **'{agendamento['filme']}'** às {hora_formatada}! ✨"
                await canal.send(msg)
                await agendamentos_db.update_one({'_id': agendamento['_id']}, {'$push': {'lembretes_enviados': 'diario'}})

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
                return await ctx.send('formato inválido. use: `!agendar nome [nome] data [d/m/a] hora [h:m]`')

            formato_data = '%d/%m/%Y' if len(data_str.split('/')[-1]) == 4 else '%d/%m/%y'
            data_hora_sem_fuso = datetime.strptime(f"{data_str} {hora_str}", f'{formato_data} %H:%M')
            data_hora_agendamento = self.fuso_horario.localize(data_hora_sem_fuso)

            if data_hora_agendamento < datetime.now(self.fuso_horario):
                return await ctx.send("ei, viajante no tempo! não podemos agendar coisas no passado.")

            novo_agendamento = {'filme': nome_filme, 'data_iso': data_hora_agendamento.isoformat(), 'canal_id': ctx.channel.id, 'lembretes_enviados': []}
            await agendamentos_db.insert_one(novo_agendamento)
            
            await ctx.send(f"boa! sessão de **'{nome_filme}'** agendada para {data_str} às {hora_str}. eu vou lembrar vocês, prometo.")
        except Exception as e:
            print(f"Erro no !agendar: {e}")
            await ctx.send("algo deu errado no agendamento. verifique o formato da data e hora.")

    @commands.command(name='agenda')
    async def _agenda(self, ctx):
        cursor = agendamentos_db.find({}).sort("data_iso")
        agendamentos = await cursor.to_list(length=None)
        if not agendamentos: return await ctx.send("não temos nenhuma sessão de cinema marcada. `!agendar`?")
        
        embed = discord.Embed(title="🗓️ Próximas Sessões Agendadas", color=discord.Color.teal())
        desc = ""
        for agendamento in agendamentos:
            data_hora_utc = datetime.fromisoformat(agendamento['data_iso'])
            data_hora_local = data_hora_utc.astimezone(self.fuso_horario)
            desc += f"**🎬 {agendamento['filme']}**\n- **Quando:** {data_hora_local.strftime('%d/%m/%Y às %H:%M')}\n"
        embed.description = desc
        await ctx.send(embed=embed)
    
    @commands.command(name='cancelar')
    async def _cancelar(self, ctx, *, nome_para_cancelar: str):
        nome_limpo = nome_para_cancelar.strip('"')
        nome_sanitizado = sanitizar_nome(nome_limpo)
        
        resultado = await agendamentos_db.delete_one({'filme': {'$regex': f'^{nome_limpo}$', '$options': 'i'}})

        if resultado.deleted_count > 0:
            await ctx.send(f"agendamento de '{nome_limpo}' cancelado. fica pra próxima então.")
        else: await ctx.send(f"não achei nenhum agendamento para '{nome_limpo}'.")

async def setup(bot):
    await bot.add_cog(Agenda(bot))