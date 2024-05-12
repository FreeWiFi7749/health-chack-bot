import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
import re
import pathlib
from datetime import datetime
import logging
import traceback
import sys
import asyncio

from utils import presence
from utils.logging import save_log
from utils import error

load_dotenv()

session_id = None

class SessionIDHandler(logging.Handler):
    def emit(self, record):
        global session_id
        message = record.getMessage()
        match = re.search(r'Session ID: ([a-f0-9]+)', message)
        if match:
            session_id = match.group(1)
            print(f"セッションIDを検出しました: {session_id}")

logger = logging.getLogger('discord.gateway')
logger.setLevel(logging.INFO)
logger.addHandler(SessionIDHandler())

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

TOKEN = os.getenv('BOT_TOKEN')
command_prefix = ['hc/']
main_guild_id = int(os.getenv('MAIN_GUILD_ID'))

class MyBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initialized = False
        self.cog_classes = {}

    async def logo(self):
        logging.info("-" * 15)
        logging.info(" _    _  _____   ____   ____ _______ ")
        logging.info("| |  | |/ ____| |  _ \ / __ \__   __|")
        logging.info("| |__| | |      | |_) | |  | | | |   ")
        logging.info("|  __  | |      |  _ <| |  | | | |   ")
        logging.info("| |  | | |____  | |_) | |__| | | |   ")
        logging.info("|_|  |_|\_____| |____/ \____/  |_|   ")
        logging.info("-" * 15)
        logging.info("Authors: FreeWiFi")
        logging.info("-" * 15)
        logging.info("discord.py: v%s", discord.__version__)
        logging.info("Python: v%s", '.'.join(map(str, sys.version_info[:3])))

    async def setup_hook(self):
        self.loop.create_task(self.after_ready())

    async def after_ready(self):
        await self.wait_until_ready()
        print("setup_hook is called")
        await self.change_presence(activity=discord.Game(name="起動中.."))
        await self.load_cogs('cogs')
        await self.tree.sync()
        if not self.initialized:
            print("Initializing...")
            self.initialized = True
            print('------')
            print('All cogs have been loaded and bot is ready.')
            print('------')
            self.loop.create_task(presence.update_presence(self))

    async def on_ready(self):
        print("on_ready is called")
        await self.logo()
        log_data = {
            "event": "BotReady",
            "description": f"{self.user} has successfully connected to Discord.",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "session_id": session_id
        }
        save_log(log_data)
        if not self.initialized:
            try:
                logging.info("ahfuiahfuhauofouafhuahfiufuuwafafauifhafwuiuiafhja")
            except Exception as e:
                print(f"Error during startup: {e}")
            self.initialized = True

    async def load_cogs(self, folder_name: str):
        cur = pathlib.Path('.')
        for p in cur.glob(f"{folder_name}/**/*.py"):
            if p.stem == "__init__" or "backup" in p.parts:
                continue
            try:
                cog_path = p.relative_to(cur).with_suffix('').as_posix().replace('/', '.')
                await self.load_extension(cog_path)
                print(f'{cog_path} loaded successfully.')
            except commands.ExtensionFailed as e:
                traceback.print_exc()
                print(f'Failed to load extension {p.stem}: {e}\nFull error: {e.__cause__}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exc):
        await error.send_error_message(ctx, exc)

intent: discord.Intents = discord.Intents.all()
bot = MyBot(command_prefix=command_prefix, intents=intent, help_command=None)
bot.run(TOKEN)
bot.run(TOKEN)