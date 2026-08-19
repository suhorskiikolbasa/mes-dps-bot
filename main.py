import discord
from discord.ext import commands
import asyncio
import config
import database as db

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

COGS = [
    'cogs.logs',
    'cogs.economy',
    'cogs.admin',
    'cogs.music',
]

@bot.event
async def on_ready():
    db.init_db()
    print(f'✅ Бот {bot.user} запущен!')
    print(f'📋 Серверов: {len(bot.guilds)}')

    # Синхронизация slash-команд
    try:
        synced = await bot.tree.sync()
        print(f'✅ Синхронизировано {len(synced)} slash-команд')
    except Exception as e:
        print(f'❌ Ошибка синхронизации: {e}')

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name='МЭС ДПС УГИБДД'
        )
    )

@bot.event
async def on_member_join(member):
    """Автовыдача роли Гражданин"""
    guild = member.guild
    role = discord.utils.get(guild.roles, name='Гражданин')

    if role is None:
        role = await guild.create_role(
            name='Гражданин',
            colour=discord.Colour.blue(),
            reason='Автоматически создано ботом МЭС ДПС'
        )

    await member.add_roles(role)
    print(f'✅ Роль [Гражданин] выдана: {member.name}')

    # Приветствие в канал
    welcome_channel = discord.utils.find(
        lambda c: c.name in ['общий', 'welcome', 'приветствие', 'главная', 'general'],
        guild.text_channels
    )
    if welcome_channel:
        embed = discord.Embed(
            title='👮 Новый участник!',
            description=f'{member.mention} присоединился к серверу!\nРоль **Гражданин** выдана автоматически.',
            color=0xc8a84b
        )
        embed.set_footer(text='МЭС ДПС УГИБДД по Красносельскому р-ну')
        await welcome_channel.send(embed=embed)

    # ЛС
    try:
        embed = discord.Embed(
            title='👮 Добро пожаловать!',
            description=f'Привет, **{member.name}**!\nТы на сервере **{guild.name}**.\nТебе выдана роль **Гражданин**.',
            color=0xc8a84b
        )
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

    # Лог
    log_cog = bot.get_cog('Logs')
    if log_cog:
        await log_cog.send_log(
            guild,
            '👤 Новый участник',
            f'{member.mention} присоединился к серверу. Роль **Гражданин** выдана.',
            0x2ecc71
        )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(title='❌ Нет прав', color=0xe74c3c))

async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f'✅ Загружен: {cog}')
            except Exception as e:
                print(f'❌ Ошибка загрузки {cog}: {e}')
        await bot.start(config.TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
