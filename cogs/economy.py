import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import asyncio
import config
import database as db

def has_admin_role():
    async def predicate(interaction: discord.Interaction):
        roles = [r.name for r in interaction.user.roles]
        if any(r in config.ADMIN_ROLES for r in roles) or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            embed=error_embed('❌ Нет прав', 'У вас недостаточно прав для этой команды.'),
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)

def error_embed(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=0xe74c3c)
    e.set_footer(text='МЭС ДПС УГИБДД')
    return e

def success_embed(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=0x2ecc71)
    e.set_footer(text='МЭС ДПС УГИБДД')
    return e

def info_embed(title: str, desc: str) -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=0xc8a84b)
    e.set_footer(text='МЭС ДПС УГИБДД')
    return e

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    def check_cooldown(self, user_id: int, seconds: int) -> int:
        """Проверить кулдаун. Возвращает оставшиеся секунды или 0"""
        now = datetime.now()
        key = f'eco_{user_id}'
        if key in self.cooldowns:
            diff = (now - self.cooldowns[key]).total_seconds()
            if diff < seconds:
                return int(seconds - diff)
        self.cooldowns[key] = now
        return 0

    # ── /баланс ──
    @app_commands.command(name='баланс', description='Посмотреть свой баланс')
    async def balance(self, interaction: discord.Interaction):
        bal = db.get_balance(interaction.user.id, interaction.guild_id)
        embed = info_embed(
            f'💰 Баланс — {interaction.user.display_name}',
            f'**{bal:,} {config.CURRENCY_SYMBOL} {config.CURRENCY_NAME}**'
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ── /баланс_юзера ──
    @app_commands.command(name='баланс_юзера', description='Посмотреть баланс другого пользователя')
    @app_commands.describe(пользователь='Кого проверить')
    async def balance_user(self, interaction: discord.Interaction, пользователь: discord.Member):
        bal = db.get_balance(пользователь.id, interaction.guild_id)
        embed = info_embed(
            f'💰 Баланс — {пользователь.display_name}',
            f'**{bal:,} {config.CURRENCY_SYMBOL} {config.CURRENCY_NAME}**'
        )
        embed.set_thumbnail(url=пользователь.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # ── /ежедневно ──
    @app_commands.command(name='ежедневно', description=f'Получить ежедневную выплату')
    async def daily(self, interaction: discord.Interaction):
        last = db.get_last_daily(interaction.user.id, interaction.guild_id)
        now = datetime.now()

        if last:
            diff = (now - last).total_seconds()
            if diff < config.DAILY_COOLDOWN:
                remaining = config.DAILY_COOLDOWN - diff
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                await interaction.response.send_message(
                    embed=error_embed(
                        '⏰ Рано!',
                        f'Следующая выплата через **{hours}ч {minutes}м**'
                    ), ephemeral=True
                )
                return

        db.set_last_daily(interaction.user.id, interaction.guild_id)
        new_bal = db.add_balance(interaction.user.id, interaction.guild_id, config.DAILY_AMOUNT)
        db.log_transaction(interaction.user.id, interaction.guild_id, 'daily', config.DAILY_AMOUNT, 'Ежедневная выплата')

        embed = success_embed(
            '💸 Ежедневная выплата!',
            f'Вы получили **{config.DAILY_AMOUNT:,} {config.CURRENCY_SYMBOL}**\n'
            f'Баланс: **{new_bal:,} {config.CURRENCY_SYMBOL}**'
        )

        await interaction.response.send_message(embed=embed)

        # Лог
        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '💸 Ежедневная выплата',
                f'{interaction.user.mention} получил **{config.DAILY_AMOUNT:,} {config.CURRENCY_SYMBOL}**',
                0x2ecc71
            )

    # ── /перевод ──
    @app_commands.command(name='перевод', description='Перевести деньги другому пользователю')
    @app_commands.describe(пользователь='Кому перевести', сумма='Сколько перевести')
    async def transfer(self, interaction: discord.Interaction, пользователь: discord.Member, сумма: int):
        wait = self.check_cooldown(interaction.user.id, config.ECONOMY_COOLDOWN)
        if wait:
            await interaction.response.send_message(
                embed=error_embed('⏳ Подождите', f'Команда доступна через **{wait} сек.**'),
                ephemeral=True
            )
            return

        if пользователь.bot:
            await interaction.response.send_message(embed=error_embed('❌ Ошибка', 'Нельзя переводить ботам.'), ephemeral=True)
            return

        if пользователь.id == interaction.user.id:
            await interaction.response.send_message(embed=error_embed('❌ Ошибка', 'Нельзя переводить самому себе.'), ephemeral=True)
            return

        if сумма <= 0:
            await interaction.response.send_message(embed=error_embed('❌ Ошибка', 'Сумма должна быть больше нуля.'), ephemeral=True)
            return

        success, new_bal = db.remove_balance(interaction.user.id, interaction.guild_id, сумма)
        if not success:
            await interaction.response.send_message(
                embed=error_embed('❌ Недостаточно средств', f'У вас только **{new_bal:,} {config.CURRENCY_SYMBOL}**'),
                ephemeral=True
            )
            return

        recv_bal = db.add_balance(пользователь.id, interaction.guild_id, сумма)
        db.log_transaction(interaction.user.id, interaction.guild_id, 'transfer_out', сумма, f'Перевод → {пользователь.id}')
        db.log_transaction(пользователь.id, interaction.guild_id, 'transfer_in', сумма, f'Перевод ← {interaction.user.id}')

        embed = success_embed(
            '💳 Перевод выполнен!',
            f'**{interaction.user.mention}** → **{пользователь.mention}**\n'
            f'Сумма: **{сумма:,} {config.CURRENCY_SYMBOL}**\n'
            f'Ваш баланс: **{new_bal:,} {config.CURRENCY_SYMBOL}**'
        )
        await interaction.response.send_message(embed=embed)

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '💳 Перевод',
                f'{interaction.user.mention} → {пользователь.mention}: **{сумма:,} {config.CURRENCY_SYMBOL}**',
                0x3498db
            )

    # ── /топ ──
    @app_commands.command(name='топ', description='Топ богатейших пользователей сервера')
    async def top(self, interaction: discord.Interaction):
        rows = db.get_top_balances(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message(embed=error_embed('❌', 'Нет данных.'), ephemeral=True)
            return

        desc = ''
        medals = ['🥇', '🥈', '🥉']
        for i, row in enumerate(rows):
            medal = medals[i] if i < 3 else f'**{i+1}.**'
            member = interaction.guild.get_member(row['user_id'])
            name = member.display_name if member else f'ID:{row["user_id"]}'
            desc += f'{medal} {name} — **{row["balance"]:,} {config.CURRENCY_SYMBOL}**\n'

        embed = info_embed('🏆 Топ богатейших', desc)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
