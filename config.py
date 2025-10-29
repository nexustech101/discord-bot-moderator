import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    """Central configuration for the Discord bot"""
    
    # Discord Settings
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    DISCORD_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
    BOT_PREFIX: str = os.getenv("BOT_PREFIX", "!")
    BOT_OWNER_ID: Optional[int] = int(os.getenv("BOT_OWNER_ID", "0")) or None
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot_data.db")
    
    # Google Sheets
    GOOGLE_SHEETS_ENABLED: bool = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    GOOGLE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    
    # Web Dashboard
    DASHBOARD_ENABLED: bool = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "5000"))
    DASHBOARD_SECRET_KEY: str = os.getenv("DASHBOARD_SECRET_KEY", "change-me-in-production")
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "127.0.0.1")
    
    # Moderation
    PROFANITY_FILTER_ENABLED: bool = os.getenv("PROFANITY_FILTER_ENABLED", "true").lower() == "true"
    SPAM_DETECTION_ENABLED: bool = os.getenv("SPAM_DETECTION_ENABLED", "true").lower() == "true"
    AUTO_MOD_ENABLED: bool = os.getenv("AUTO_MOD_ENABLED", "true").lower() == "true"
    ML_MODERATION_ENABLED: bool = os.getenv("ML_MODERATION_ENABLED", "false").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/bot.log")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    MAX_COMMANDS_PER_MINUTE: int = int(os.getenv("MAX_COMMANDS_PER_MINUTE", "10"))
    
    # Survey Settings
    MAX_SURVEY_QUESTIONS: int = int(os.getenv("MAX_SURVEY_QUESTIONS", "20"))
    SURVEY_TIMEOUT_HOURS: int = int(os.getenv("SURVEY_TIMEOUT_HOURS", "168"))
    
    # Auto Roles
    AUTO_ROLE_ENABLED: bool = os.getenv("AUTO_ROLE_ENABLED", "true").lower() == "true"
    NEW_MEMBER_ROLE_NAME: str = os.getenv("NEW_MEMBER_ROLE_NAME", "New Member")
    
    # Scheduled Messages
    SCHEDULED_MESSAGES_ENABLED: bool = os.getenv("SCHEDULED_MESSAGES_ENABLED", "true").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is required")
        return True

# Default profanity list (can be extended by clients)
DEFAULT_PROFANITY_LIST = [
    "badword1", "badword2", "badword3"
    # Add more as needed
]

# Default spam detection settings
SPAM_SETTINGS = {
    "max_messages": 5,
    "time_window": 5,  # seconds
    "max_mentions": 5,
    "max_emojis": 10,
    "duplicate_threshold": 3
}

# Embed colors for consistent branding
EMBED_COLORS = {
    "success": 0x00ff00,
    "error": 0xff0000,
    "info": 0x3498db,
    "warning": 0xffaa00,
    "survey": 0x9b59b6
}
