import discord
from discord.ext import commands
import asyncio
import sys
from pathlib import Path

from config import Config
from utils.database import Database
from utils.logger import setup_logger

# Initialize logger
logger = setup_logger()

class CommunityBot(commands.Bot):
    """Main Discord Bot class"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
            description="Community Management Bot with Surveys & Moderation"
        )
        
        self.db = Database()
        self.start_time = None
    
    async def get_prefix(self, message):
        """Get dynamic prefix for each guild"""
        if not message.guild:
            return Config.BOT_PREFIX
        
        guild_data = await self.db.get_guild(message.guild.id)
        if guild_data and guild_data.get('prefix'):
            return guild_data['prefix']
        return Config.BOT_PREFIX
    
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        logger.info("Starting bot setup...")
        
        # Connect to database
        await self.db.connect()
        logger.info("Database connected")
        
        # Load cogs
        await self.load_cogs()
        logger.info("All cogs loaded")
    
    async def load_cogs(self):
        """Load all cog modules"""
        cogs_dir = Path("cogs")
        
        if not cogs_dir.exists():
            logger.warning("Cogs directory not found")
            return
        
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.stem.startswith("_"):
                continue
            
            try:
                await self.load_extension(f"cogs.{cog_file.stem}")
                logger.info(f"Loaded cog: {cog_file.stem}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_file.stem}: {e}")
    
    async def on_ready(self):
        """Event triggered when bot is ready"""
        self.start_time = discord.utils.utcnow()
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Bot is ready!")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{Config.BOT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
    
    async def on_guild_join(self, guild: discord.Guild):
        """Event triggered when bot joins a guild"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Add guild to database
        await self.db.add_guild(guild.id, guild.name)
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{Config.BOT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Event triggered when bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Update presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{Config.BOT_PREFIX}help | {len(self.guilds)} servers"
            )
        )
    
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided.")
            return
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ Command on cooldown. Try again in {error.retry_after:.1f}s")
            return
        
        # Log unexpected errors
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)
        await ctx.send("❌ An unexpected error occurred. The issue has been logged.")
    
    async def close(self):
        """Cleanup before shutdown"""
        logger.info("Shutting down bot...")
        await self.db.close()
        await super().close()

async def main():
    """Main entry point"""
    try:
        # Validate configuration
        Config.validate()
        
        # Create and run bot
        bot = CommunityBot()
        
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=e)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
