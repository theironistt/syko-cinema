# cogs/agenda.py
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import pytz
from utils import agendamentos_db, parse_args, sanitizar_nome

class Agenda(commands.Cog):
    # ... (código do Agenda.py reescrito para usar agendamentos_db)
    pass
async def setup(bot):
    await bot.add_cog(Agenda(bot))