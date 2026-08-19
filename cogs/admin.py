import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import config
import database as db

def has_admin_role():
    async def predicate(interaction: discord.Interaction):
        roles = [r.name for r in interaction.user.roles]
        if any(r in config.ADMIN_ROLES for r in roles) or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(title='❌ Нет прав', description='У вас недостаточно прав.', color=0xe74c3c),
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)

def error_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0xe74c3c)

def success_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0x2ecc71)

def info_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0xc8a84b)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── /выдать_деньги ──
    @app_commands.command(name='выдать_деньги', description='[АДМИН] Выдать деньги пользователю')
    @app_commands.describe(пользователь='Кому выдать', сумма='Сколько выдать')
    @has_admin_role()
    async def give_money(self, interaction: discord.Interaction, пользователь: discord.Member, сумма: int):
        if сумма <= 0:
            await interaction.response.send_message(embed=error_embed('❌', 'Сумма должна быть больше нуля.'), ephemeral=True)
            return

        new_bal = db.add_balance(пользователь.id, interaction.guild_id, сумма)
        db.log_transaction(пользователь.id, interaction.guild_id, 'admin_add', сумма, f'Выдано администратором {interaction.user.id}')

        embed = success_embed(
            '✅ Деньги выданы',
            f'Пользователь: {пользователь.mention}\n'
            f'Выдано: **{сумма:,} {config.CURRENCY_SYMBOL}**\n'
            f'Новый баланс: **{new_bal:,} {config.CURRENCY_SYMBOL}**'
        )
        await interaction.response.send_message(embed=embed)

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '✅ Выдача денег [АДМИН]',
                f'Администратор {interaction.user.mention} выдал **{сумма:,} {config.CURRENCY_SYMBOL}** → {пользователь.mention}',
                0x2ecc71
            )

    # ── /забрать_деньги ──
    @app_commands.command(name='забрать_деньги', description='[АДМИН] Забрать деньги у пользователя')
    @app_commands.describe(пользователь='У кого забрать', сумма='Сколько забрать')
    @has_admin_role()
    async def take_money(self, interaction: discord.Interaction, пользователь: discord.Member, сумма: int):
        if сумма <= 0:
            await interaction.response.send_message(embed=error_embed('❌', 'Сумма должна быть больше нуля.'), ephemeral=True)
            return

        success, new_bal = db.remove_balance(пользователь.id, interaction.guild_id, сумма)
        if not success:
            await interaction.response.send_message(
                embed=error_embed('❌ Недостаточно средств', f'У пользователя только **{new_bal:,} {config.CURRENCY_SYMBOL}**'),
                ephemeral=True
            )
            return

        db.log_transaction(пользователь.id, interaction.guild_id, 'admin_remove', сумма, f'Снято администратором {interaction.user.id}')

        embed = success_embed(
            '✅ Деньги забраны',
            f'Пользователь: {пользователь.mention}\n'
            f'Забрано: **{сумма:,} {config.CURRENCY_SYMBOL}**\n'
            f'Новый баланс: **{new_bal:,} {config.CURRENCY_SYMBOL}**'
        )
        await interaction.response.send_message(embed=embed)

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '❌ Снятие денег [АДМИН]',
                f'Администратор {interaction.user.mention} забрал **{сумма:,} {config.CURRENCY_SYMBOL}** у {пользователь.mention}',
                0xe74c3c
            )

    # ── /баланс_игрока ──
    @app_commands.command(name='баланс_игрока', description='[АДМИН] Посмотреть баланс пользователя')
    @app_commands.describe(пользователь='Чей баланс')
    @has_admin_role()
    async def check_balance(self, interaction: discord.Interaction, пользователь: discord.Member):
        bal = db.get_balance(пользователь.id, interaction.guild_id)
        embed = info_embed(
            f'💰 Баланс — {пользователь.display_name}',
            f'**{bal:,} {config.CURRENCY_SYMBOL} {config.CURRENCY_NAME}**'
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /журнал ──
    @app_commands.command(name='журнал', description='[АДМИН] Просмотреть журнал транзакций')
    @has_admin_role()
    async def journal(self, interaction: discord.Interaction):
        rows = db.get_transactions(interaction.guild_id, 15)
        if not rows:
            await interaction.response.send_message(embed=error_embed('❌', 'Журнал пуст.'), ephemeral=True)
            return

        actions = {
            'daily': '💸 Ежедневно',
            'transfer_out': '📤 Перевод (отправка)',
            'transfer_in': '📥 Перевод (получение)',
            'admin_add': '✅ Выдача [АДМИН]',
            'admin_remove': '❌ Снятие [АДМИН]',
        }

        desc = ''
        for row in rows:
            member = interaction.guild.get_member(row['user_id'])
            name = member.display_name if member else f'ID:{row["user_id"]}'
            action = actions.get(row['action'], row['action'])
            time = row['timestamp'][:16].replace('T', ' ')
            desc += f'`{time}` {action} — **{name}** — {row["amount"]:,} {config.CURRENCY_SYMBOL}\n'

        embed = info_embed('📋 Журнал транзакций (последние 15)', desc)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /обнулить ──
    @app_commands.command(name='обнулить', description='[АДМИН] Обнулить баланс пользователя')
    @app_commands.describe(пользователь='Кому обнулить')
    @has_admin_role()
    async def reset_balance(self, interaction: discord.Interaction, пользователь: discord.Member):
        db.set_balance(пользователь.id, interaction.guild_id, 0)
        db.log_transaction(пользователь.id, interaction.guild_id, 'admin_reset', 0, f'Обнуление администратором {interaction.user.id}')
        embed = success_embed('✅ Баланс обнулён', f'Баланс {пользователь.mention} обнулён.')
        await interaction.response.send_message(embed=embed)

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '🔄 Обнуление баланса [АДМИН]',
                f'{interaction.user.mention} обнулил баланс {пользователь.mention}',
                0xe67e22
            )

async def setup(bot):
    await bot.add_cog(Admin(bot))
