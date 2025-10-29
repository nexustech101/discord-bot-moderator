import discord
from discord.ext import commands
from typing import Optional, Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
import re

from config import Config, DEFAULT_PROFANITY_LIST, SPAM_SETTINGS
from utils.helpers import *
from utils.logger import setup_logger

logger = setup_logger("Moderation")

# Optional ML moderation import
if Config.ML_MODERATION_ENABLED:
    try:
        from model import ModerationModel
        ml_model = ModerationModel()
        logger.info("ML Moderation enabled")
    except ImportError:
        logger.warning("model.py not found. ML moderation disabled.")
        ml_model = None
else:
    ml_model = None

class Moderation(commands.Cog):
    """Moderation and auto-mod features"""
    
    def __init__(self, bot):
        self.bot = bot
        self.profanity_list = set(DEFAULT_PROFANITY_LIST)
        self.spam_tracker = defaultdict(list)
        self.message_history = defaultdict(list)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Auto-assign role when member joins"""
        if not Config.AUTO_ROLE_ENABLED:
            return
        
        # Find the auto-role
        auto_role = discord.utils.get(member.guild.roles, name=Config.NEW_MEMBER_ROLE_NAME)
        
        if auto_role:
            try:
                await member.add_roles(auto_role)
                logger.info(f"Assigned {auto_role.name} to {member.name} in {member.guild.name}")
            except discord.Forbidden:
                logger.error(f"Missing permissions to assign role in {member.guild.name}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages for moderation"""
        if message.author.bot or not message.guild:
            return
        
        # Skip if auto-mod is disabled
        if not Config.AUTO_MOD_ENABLED:
            return
        
        # Check profanity
        if Config.PROFANITY_FILTER_ENABLED:
            if await self.check_profanity(message):
                return
        
        # Check spam
        if Config.SPAM_DETECTION_ENABLED:
            if await self.check_spam(message):
                return
        
        # ML-based moderation (premium feature)
        if ml_model and Config.ML_MODERATION_ENABLED:
            await self.ml_moderate(message)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log deleted messages"""
        if message.author.bot or not message.guild:
            return
        
        # Store in database
        await self.bot.db.log_deleted_message(
            message.guild.id,
            message.channel.id,
            message.author.id,
            message.content
        )
        
        logger.info(f"Logged deleted message from {message.author} in {message.guild.name}")
    
    async def check_profanity(self, message: discord.Message) -> bool:
        """Check message for profanity"""
        content_lower = message.content.lower()
        
        for word in self.profanity_list:
            if re.search(r'\b' + re.escape(word) + r'\b', content_lower):
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} Please watch your language!",
                        delete_after=5
                    )
                    
                    # Log the action
                    await self.bot.db.log_moderation_action(
                        message.guild.id,
                        message.author.id,
                        self.bot.user.id,
                        "profanity_filter",
                        f"Deleted message containing: {word}"
                    )
                    
                    logger.info(f"Deleted profane message from {message.author} in {message.guild.name}")
                    return True
                except discord.Forbidden:
                    logger.error(f"Missing permissions to delete message in {message.guild.name}")
        
        return False
    
    async def check_spam(self, message: discord.Message) -> bool:
        """Check for spam patterns"""
        user_id = message.author.id
        now = datetime.utcnow()
        
        # Track messages
        self.spam_tracker[user_id].append(now)
        self.message_history[user_id].append(message.content)
        
        # Clean old entries
        self.spam_tracker[user_id] = [
            msg_time for msg_time in self.spam_tracker[user_id]
            if now - msg_time < timedelta(seconds=SPAM_SETTINGS['time_window'])
        ]
        
        # Keep only recent messages
        if len(self.message_history[user_id]) > 10:
            self.message_history[user_id] = self.message_history[user_id][-10:]
        
        # Check message frequency
        if len(self.spam_tracker[user_id]) > SPAM_SETTINGS['max_messages']:
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Slow down! You're sending messages too quickly.",
                    delete_after=5
                )
                
                await self.bot.db.log_moderation_action(
                    message.guild.id,
                    message.author.id,
                    self.bot.user.id,
                    "spam_detection",
                    "Message frequency exceeded limit"
                )
                
                logger.info(f"Spam detected from {message.author} in {message.guild.name}")
                return True
            except discord.Forbidden:
                pass
        
        # Check duplicate messages
        recent_messages = self.message_history[user_id][-5:]
        if len(recent_messages) >= SPAM_SETTINGS['duplicate_threshold']:
            if len(set(recent_messages)) == 1:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} Please don't spam the same message.",
                        delete_after=5
                    )
                    
                    await self.bot.db.log_moderation_action(
                        message.guild.id,
                        message.author.id,
                        self.bot.user.id,
                        "spam_detection",
                        "Duplicate message spam"
                    )
                    return True
                except discord.Forbidden:
                    pass
        
        return False
    
    async def ml_moderate(self, message: discord.Message):
        """Use ML model for advanced moderation (premium feature)"""
        try:
            prediction = ml_model.predict(message.content)
            
            if prediction['is_toxic'] and prediction['confidence'] > 0.8:
                await message.delete()
                
                embed = warning_embed(
                    "Message Removed",
                    f"{message.author.mention} Your message was flagged by our AI moderation system."
                )
                await message.channel.send(embed=embed, delete_after=10)
                
                await self.bot.db.log_moderation_action(
                    message.guild.id,
                    message.author.id,
                    self.bot.user.id,
                    "ml_moderation",
                    f"Toxic content detected (confidence: {prediction['confidence']:.2f})"
                )
                
                logger.info(f"ML moderation removed message from {message.author}")
        except Exception as e:
            logger.error(f"ML moderation error: {e}")
    
    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn_user(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a user"""
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ You cannot warn someone with equal or higher role.")
            return
        
        # Add warning to database
        await self.bot.db.add_warning(
            ctx.guild.id,
            member.id,
            ctx.author.id,
            reason
        )
        
        # Get total warnings
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)
        warning_count = len(warnings)
        
        embed = warning_embed(
            "User Warned",
            f"{member.mention} has been warned.\n**Reason:** {reason}\n**Total Warnings:** {warning_count}"
        )
        await ctx.send(embed=embed)
        
        # DM the user
        try:
            dm_embed = warning_embed(
                f"Warning in {ctx.guild.name}",
                f"You have been warned by {ctx.author.mention}.\n**Reason:** {reason}\n**Total Warnings:** {warning_count}"
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        
        logger.info(f"{ctx.author} warned {member} in {ctx.guild.name}")
    
    @commands.command(name="warnings")
    async def check_warnings(self, ctx, member: discord.Member = None):
        """Check warnings for a user"""
        member = member or ctx.author
        
        warnings = await self.bot.db.get_warnings(ctx.guild.id, member.id)
        
        if not warnings:
            await ctx.send(f"{member.mention} has no warnings.")
            return
        
        embed = info_embed(
            f"Warnings for {member.display_name}",
            f"Total: {len(warnings)}"
        )
        
        for idx, warning in enumerate(warnings[:10], 1):
            moderator = ctx.guild.get_member(warning['moderator_id'])
            mod_name = moderator.display_name if moderator else "Unknown"
            
            embed.add_field(
                name=f"Warning #{idx}",
                value=f"**Reason:** {warning['reason']}\n**By:** {mod_name}\n**Date:** {warning['timestamp']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member"""
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ You cannot kick someone with equal or higher role.")
            return
        
        try:
            await member.kick(reason=reason)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id,
                member.id,
                ctx.author.id,
                "kick",
                reason
            )
            
            embed = success_embed("Member Kicked", f"{member.mention} has been kicked.\n**Reason:** {reason}")
            await ctx.send(embed=embed)
            
            logger.info(f"{ctx.author} kicked {member} from {ctx.guild.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick that user.")
    
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member"""
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ You cannot ban someone with equal or higher role.")
            return
        
        try:
            await member.ban(reason=reason)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id,
                member.id,
                ctx.author.id,
                "ban",
                reason
            )
            
            embed = success_embed("Member Banned", f"{member.mention} has been banned.\n**Reason:** {reason}")
            await ctx.send(embed=embed)
            
            logger.info(f"{ctx.author} banned {member} from {ctx.guild.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that user.")
    
    @commands.command(name="mute")
    @commands.has_permissions(manage_roles=True)
    async def mute_member(self, ctx, member: discord.Member, duration: int = 60, *, reason: str = "No reason provided"):
        """Timeout a member (in minutes)"""
        try:
            await member.timeout(timedelta(minutes=duration), reason=reason)
            
            await self.bot.db.log_moderation_action(
                ctx.guild.id,
                member.id,
                ctx.author.id,
                "timeout",
                f"{reason} (Duration: {duration}m)"
            )
            
            embed = success_embed(
                "Member Timed Out",
                f"{member.mention} has been timed out for {duration} minutes.\n**Reason:** {reason}"
            )
            await ctx.send(embed=embed)
            
            logger.info(f"{ctx.author} muted {member} for {duration}m in {ctx.guild.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to timeout that user.")
    
    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge_messages(self, ctx, amount: int = 10):
        """Delete multiple messages"""
        if amount < 1 or amount > 100:
            await ctx.send("❌ Amount must be between 1 and 100.")
            return
        
        try:
            deleted = await ctx.channel.purge(limit=amount + 1)
            
            embed = success_embed("Messages Purged", f"Deleted {len(deleted) - 1} messages.")
            await ctx.send(embed=embed, delete_after=5)
            
            logger.info(f"{ctx.author} purged {len(deleted)} messages in {ctx.guild.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to delete messages.")
    
    @commands.command(name="addprofanity")
    @commands.has_permissions(administrator=True)
    async def add_profanity(self, ctx, *, word: str):
        """Add word to profanity filter"""
        self.profanity_list.add(word.lower())
        await ctx.send(f"✅ Added `{word}` to profanity filter.")
        logger.info(f"{ctx.author} added '{word}' to profanity filter")
    
    @commands.command(name="lockdown")
    @commands.has_permissions(manage_channels=True)
    async def lockdown_channel(self, ctx):
        """Lock down the current channel"""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
            embed = warning_embed("Channel Locked", "This channel has been locked down.")
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} locked down #{ctx.channel.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this channel.")
    
    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx):
        """Unlock the current channel"""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
            embed = success_embed("Channel Unlocked", "This channel has been unlocked.")
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} unlocked #{ctx.channel.name}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage this channel.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
