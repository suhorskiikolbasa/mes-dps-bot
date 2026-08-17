import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
ROLE_NAME = 'Гражданин'  # Название роли которую выдавать

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен и работает!')
    print(f'📋 Серверов: {len(bot.guilds)}')

@bot.event
async def on_member_join(member):
    """Выдаёт роль Гражданин всем кто заходит на сервер"""
    guild = member.guild

    # Ищем роль по имени
    role = discord.utils.get(guild.roles, name=ROLE_NAME)

    if role is None:
        # Если роли нет — создаём её
        role = await guild.create_role(
            name=ROLE_NAME,
            colour=discord.Colour.blue(),
            reason='Автоматически создано ботом МЭС ДПС'
        )
        print(f'🆕 Создана роль: {ROLE_NAME}')

    # Выдаём роль
    await member.add_roles(role)
    print(f'✅ Роль [{ROLE_NAME}] выдана: {member.name}')

    # Приветственное сообщение в личку
    try:
        embed = discord.Embed(
            title='👮 Добро пожаловать!',
            description=(
                f'Привет, **{member.name}**!\n\n'
                f'Ты на сервере **{guild.name}**.\n'
                f'Тебе выдана роль **{ROLE_NAME}**.\n\n'
                '📋 Ознакомься с правилами сервера.'
            ),
            colour=discord.Colour.gold()
        )
        embed.set_footer(text='МЭС ДПС УГИБДД по Красносельскому р-ну')
        await member.send(embed=embed)
    except discord.Forbidden:
        # Если личные сообщения закрыты — пропускаем
        print(f'⚠️ Не удалось отправить ЛС: {member.name}')

    # Приветствие в канале если есть канал "общий" или "welcome"
    welcome_channel = discord.utils.find(
        lambda c: c.name in ['общий', 'welcome', 'приветствие', 'главная', 'general'],
        guild.text_channels
    )
    if welcome_channel:
        embed = discord.Embed(
            title='👮 Новый участник!',
            description=(
                f'{member.mention} присоединился к серверу!\n'
                f'Роль **{ROLE_NAME}** выдана автоматически.'
            ),
            colour=discord.Colour.gold()
        )
        embed.set_footer(text='МЭС ДПС УГИБДД по Красносельскому р-ну')
        await welcome_channel.send(embed=embed)

# ── КОМАНДЫ ──

@bot.command(name='выдатьроль')
@commands.has_permissions(administrator=True)
async def give_role(ctx, member: discord.Member):
    """Вручную выдать роль Гражданин (только для админов)"""
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    if role is None:
        role = await ctx.guild.create_role(name=ROLE_NAME, colour=discord.Colour.blue())
    await member.add_roles(role)
    await ctx.send(f'✅ Роль **{ROLE_NAME}** выдана {member.mention}')

@bot.command(name='выдатьвсем')
@commands.has_permissions(administrator=True)
async def give_all(ctx):
    """Выдать роль Гражданин всем участникам без роли (кроме ботов)"""
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    if role is None:
        role = await ctx.guild.create_role(name=ROLE_NAME, colour=discord.Colour.blue())

    count = 0
    async with ctx.typing():
        for member in ctx.guild.members:
            if not member.bot and role not in member.roles:
                await member.add_roles(role)
                count += 1

    await ctx.send(f'✅ Роль **{ROLE_NAME}** выдана **{count}** участникам!')

@bot.command(name='статус')
@commands.has_permissions(administrator=True)
async def status(ctx):
    """Показать статус бота"""
    embed = discord.Embed(
        title='📊 Статус бота МЭС ДПС',
        colour=discord.Colour.gold()
    )
    embed.add_field(name='Сервер', value=ctx.guild.name, inline=True)
    embed.add_field(name='Участников', value=ctx.guild.member_count, inline=True)
    embed.add_field(name='Авто-роль', value=ROLE_NAME, inline=True)
    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME)
    embed.add_field(name='Роль существует', value='✅ Да' if role else '❌ Нет', inline=True)
    embed.set_footer(text='МЭС ДПС УГИБДД по Красносельскому р-ну')
    await ctx.send(embed=embed)

bot.run(TOKEN)
