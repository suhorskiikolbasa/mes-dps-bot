import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
from collections import deque
import config

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

def error_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0xe74c3c)

def success_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0x2ecc71)

def info_embed(title, desc):
    return discord.Embed(title=title, description=desc, color=0xc8a84b)

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.volume = config.DEFAULT_VOLUME / 100
        self.is_playing = False

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def get_queue(self, guild_id) -> MusicQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def get_audio_info(self, query: str):
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            try:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if 'entries' in info:
                    info = info['entries'][0]
                return {
                    'url': info['url'],
                    'title': info.get('title', 'Неизвестный трек'),
                    'duration': info.get('duration', 0),
                    'webpage_url': info.get('webpage_url', ''),
                }
            except Exception as e:
                return None

    def play_next(self, guild_id, voice_client):
        queue = self.get_queue(guild_id)
        if queue.queue:
            track = queue.queue.popleft()
            queue.current = track
            queue.is_playing = True

            source = discord.FFmpegPCMAudio(track['url'], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=queue.volume)

            def after_play(error):
                queue.is_playing = False
                queue.current = None
                if error:
                    print(f'Ошибка воспроизведения: {error}')
                asyncio.run_coroutine_threadsafe(
                    self.auto_next(guild_id, voice_client), self.bot.loop
                )

            voice_client.play(source, after=after_play)
        else:
            queue.is_playing = False
            queue.current = None

    async def auto_next(self, guild_id, voice_client):
        queue = self.get_queue(guild_id)
        if queue.queue and voice_client.is_connected():
            self.play_next(guild_id, voice_client)

    # ── /играть ──
    @app_commands.command(name='играть', description='Включить музыку (название или ссылка)')
    @app_commands.describe(запрос='Название трека или YouTube ссылка')
    async def play(self, interaction: discord.Interaction, запрос: str):
        if not interaction.user.voice:
            await interaction.response.send_message(
                embed=error_embed('❌ Ошибка', 'Вы не в голосовом канале!'), ephemeral=True
            )
            return

        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        queue = self.get_queue(interaction.guild_id)

        if len(queue.queue) >= config.MAX_QUEUE_SIZE:
            await interaction.followup.send(
                embed=error_embed('❌ Очередь полна', f'Максимум {config.MAX_QUEUE_SIZE} треков в очереди.')
            )
            return

        track = await self.get_audio_info(запрос)
        if not track:
            await interaction.followup.send(
                embed=error_embed('❌ Не найдено', 'Трек не найден. Попробуйте другой запрос.')
            )
            return

        duration = f"{track['duration'] // 60}:{track['duration'] % 60:02d}" if track['duration'] else 'неизвестно'

        if voice_client.is_playing() or queue.is_playing:
            queue.queue.append(track)
            embed = info_embed(
                '📋 Добавлено в очередь',
                f'**[{track["title"]}]({track["webpage_url"]})**\n'
                f'Длительность: `{duration}`\n'
                f'Позиция в очереди: **{len(queue.queue)}**'
            )
            await interaction.followup.send(embed=embed)
        else:
            queue.queue.append(track)
            self.play_next(interaction.guild_id, voice_client)
            embed = success_embed(
                '🎵 Сейчас играет',
                f'**[{track["title"]}]({track["webpage_url"]})**\n'
                f'Длительность: `{duration}`'
            )
            await interaction.followup.send(embed=embed)

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '🎵 Музыка запущена',
                f'{interaction.user.mention} запустил **{track["title"]}**',
                0x9b59b6
            )

    # ── /пауза ──
    @app_commands.command(name='пауза', description='Поставить музыку на паузу')
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message(embed=error_embed('❌', 'Ничего не играет.'), ephemeral=True)
            return
        vc.pause()
        await interaction.response.send_message(embed=info_embed('⏸ Пауза', 'Музыка поставлена на паузу.'))

    # ── /продолжить ──
    @app_commands.command(name='продолжить', description='Продолжить воспроизведение')
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_paused():
            await interaction.response.send_message(embed=error_embed('❌', 'Музыка не на паузе.'), ephemeral=True)
            return
        vc.resume()
        await interaction.response.send_message(embed=success_embed('▶️ Продолжено', 'Воспроизведение продолжено.'))

    # ── /пропустить ──
    @app_commands.command(name='пропустить', description='Пропустить текущий трек')
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message(embed=error_embed('❌', 'Ничего не играет.'), ephemeral=True)
            return
        vc.stop()
        await interaction.response.send_message(embed=info_embed('⏭ Пропущено', 'Трек пропущен.'))

    # ── /стоп ──
    @app_commands.command(name='стоп', description='Остановить музыку и отключить бота')
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message(embed=error_embed('❌', 'Бот не в голосовом канале.'), ephemeral=True)
            return

        queue = self.get_queue(interaction.guild_id)
        queue.queue.clear()
        queue.current = None
        queue.is_playing = False

        await vc.disconnect()
        await interaction.response.send_message(embed=info_embed('⏹ Остановлено', 'Музыка остановлена, бот отключён.'))

        log_cog = self.bot.get_cog('Logs')
        if log_cog:
            await log_cog.send_log(
                interaction.guild,
                '⏹ Музыка остановлена',
                f'{interaction.user.mention} остановил музыку.',
                0x9b59b6
            )

    # ── /очередь ──
    @app_commands.command(name='очередь', description='Показать очередь треков')
    async def queue_show(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)

        if not queue.current and not queue.queue:
            await interaction.response.send_message(embed=info_embed('📋 Очередь пуста', 'Добавьте треки через /играть'), ephemeral=True)
            return

        desc = ''
        if queue.current:
            desc += f'**▶️ Сейчас:** {queue.current["title"]}\n\n'

        if queue.queue:
            desc += '**В очереди:**\n'
            for i, track in enumerate(list(queue.queue)[:10], 1):
                desc += f'`{i}.` {track["title"]}\n'
            if len(queue.queue) > 10:
                desc += f'\n...и ещё **{len(queue.queue) - 10}** треков'

        await interaction.response.send_message(embed=info_embed(f'📋 Очередь ({len(queue.queue)} треков)', desc))

    # ── /сейчас_играет ──
    @app_commands.command(name='сейчас_играет', description='Показать текущий трек')
    async def now_playing(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if not queue.current:
            await interaction.response.send_message(embed=error_embed('❌', 'Ничего не играет.'), ephemeral=True)
            return

        track = queue.current
        duration = f"{track['duration'] // 60}:{track['duration'] % 60:02d}" if track.get('duration') else 'неизвестно'
        embed = info_embed(
            '🎵 Сейчас играет',
            f'**[{track["title"]}]({track["webpage_url"]})**\n'
            f'Длительность: `{duration}`\n'
            f'В очереди: **{len(queue.queue)}** треков'
        )
        await interaction.response.send_message(embed=embed)

    # ── /громкость ──
    @app_commands.command(name='громкость', description='Изменить громкость (1-100)')
    @app_commands.describe(уровень='Уровень громкости от 1 до 100')
    async def volume(self, interaction: discord.Interaction, уровень: int):
        if not 1 <= уровень <= 100:
            await interaction.response.send_message(embed=error_embed('❌', 'Громкость должна быть от 1 до 100.'), ephemeral=True)
            return

        vc = interaction.guild.voice_client
        queue = self.get_queue(interaction.guild_id)
        queue.volume = уровень / 100

        if vc and vc.source:
            vc.source.volume = queue.volume

        await interaction.response.send_message(embed=success_embed('🔊 Громкость', f'Установлена громкость: **{уровень}%**'))

    # ── /очистить_очередь ──
    @app_commands.command(name='очистить_очередь', description='Очистить очередь треков')
    async def clear_queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        queue.queue.clear()
        await interaction.response.send_message(embed=success_embed('🗑 Очередь очищена', 'Все треки удалены из очереди.'))

async def setup(bot):
    await bot.add_cog(Music(bot))
