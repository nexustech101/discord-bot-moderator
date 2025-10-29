import discord
from datetime import datetime
from typing import List, Dict, Optional
from config import EMBED_COLORS

def create_embed(
    title: str,
    description: str = None,
    color_key: str = "info",
    fields: List[Dict[str, str]] = None,
    footer: str = None,
    thumbnail: str = None,
    image: str = None
) -> discord.Embed:
    """Create a standardized embed"""
    
    color = EMBED_COLORS.get(color_key, EMBED_COLORS["info"])
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", "Field"),
                value=field.get("value", "No value"),
                inline=field.get("inline", False)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    return embed

def success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed"""
    return create_embed(title, description, "success")

def error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed"""
    return create_embed(title, description, "error")

def info_embed(title: str, description: str) -> discord.Embed:
    """Create an info embed"""
    return create_embed(title, description, "info")

def warning_embed(title: str, description: str) -> discord.Embed:
    """Create a warning embed"""
    return create_embed(title, description, "warning")

def is_admin(member: discord.Member) -> bool:
    """Check if member has admin permissions"""
    return member.guild_permissions.administrator

def is_moderator(member: discord.Member) -> bool:
    """Check if member has moderator permissions"""
    return (
        member.guild_permissions.administrator or
        member.guild_permissions.manage_messages or
        member.guild_permissions.kick_members or
        member.guild_permissions.ban_members
    )

def format_time(timestamp: datetime) -> str:
    """Format timestamp to readable string"""
    return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

def truncate_text(text: str, max_length: int = 1024) -> str:
    """Truncate text to fit embed limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
