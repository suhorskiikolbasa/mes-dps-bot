import discord
from discord.ext import commands
from datetime import datetime
import config

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild: discord.Guild, title: str, description: str, color: int = 0xc8a84b):
        """Отправить лог в канал логов"""
        channel = discord.utils.find(
            lambda c: c.name == config.LOG_CHANNEL_NAME,
            guild.text_channels
        )
        if not channel:
            # Пробуем найти похожий канал
            channel = discord.utils.find(
                lambda c: 'лог' in c.name.lower() or 'log' in c.name.lower(),
                guild.text_channels
            )
        if not channel:
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        embed.set_footer(text='МЭС ДПС УГИБДД | Система логов')
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(Logs(bot))
