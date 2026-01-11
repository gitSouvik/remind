import os
import asyncio
import discord
import logging
from logging.handlers import TimedRotatingFileHandler
from remind import constants

from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
from remind.util import discord_common
from remind.util import clist_api


def setup_logging():
    # Make required directories.
    for path in constants.ALL_DIRS:
        os.makedirs(path, exist_ok=True)

    logging.basicConfig(
        format='{asctime}:{levelname}:{name}:{message}',
        style='{',
        datefmt='%d-%m-%Y %H:%M:%S',
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            TimedRotatingFileHandler(
                constants.LOG_FILE_PATH,
                when='D',
                backupCount=3,
                utc=True
            )
        ]
    )


async def main():
    load_dotenv()

    token = os.getenv('BOT_TOKEN_REMIND')
    if not token:
        logging.error('Token required')
        return

    super_users_str = os.getenv('SUPER_USERS')
    if not super_users_str:
        logging.error('Superusers required')
        return
    constants.SUPER_USERS = list(map(int, super_users_str.split(",")))

    remind_moderator_role = os.getenv('REMIND_MODERATOR_ROLE')
    if remind_moderator_role:
        constants.REMIND_MODERATOR_ROLE = remind_moderator_role

    setup_logging()

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(
        command_prefix=commands.when_mentioned_or('t;'),
        intents=intents
    )

    # CHANGED: load extensions asynchronously (discord.py v2)
    cogs = [file.stem for file in Path('remind', 'cogs').glob('*.py')]

    async with bot:
        for extension in cogs:
            await bot.load_extension(f'remind.cogs.{extension}')

        logging.info(f'Cogs loaded: {", ".join(bot.cogs)}')

        def no_dm_check(ctx):
            if ctx.guild is None:
                raise commands.NoPrivateMessage('Private messages not permitted.')
            return True

        bot.add_check(no_dm_check)

        @discord_common.on_ready_event_once(bot)
        async def init():
            clist_api.cache()
            asyncio.create_task(discord_common.presence(bot))

        bot.add_listener(
            discord_common.bot_error_handler,
            name='on_command_error'
        )

        # CHANGED: use bot.start instead of bot.run
        await bot.start(token)


if __name__ == '__main__':
    # CHANGED: async entrypoint required for discord.py v2
    asyncio.run(main())