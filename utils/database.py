import aiosqlite
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import Config

class Database:
    """Async database handler for the Discord bot"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_URL.replace("sqlite:///", "")
        self.conn = None
    
    async def connect(self):
        """Establish database connection"""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.create_tables()
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def create_tables(self):
        """Create all necessary tables"""
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY,
                guild_name TEXT,
                prefix TEXT DEFAULT '!',
                auto_role_id INTEGER,
                mod_log_channel_id INTEGER,
                custom_settings TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                message_content TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                creator_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                questions TEXT NOT NULL,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS survey_responses (
                response_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                user_id INTEGER,
                answers TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (survey_id) REFERENCES surveys(survey_id)
            );
            
            CREATE TABLE IF NOT EXISTS auto_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                trigger TEXT NOT NULL,
                response TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message_content TEXT NOT NULL,
                cron_expression TEXT,
                next_run TIMESTAMP,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS user_warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                event_type TEXT,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
            );
        """)
        await self.conn.commit()
    
    # Guild methods
    async def add_guild(self, guild_id: int, guild_name: str):
        """Add or update guild"""
        await self.conn.execute(
            "INSERT OR REPLACE INTO guilds (guild_id, guild_name) VALUES (?, ?)",
            (guild_id, guild_name)
        )
        await self.conn.commit()
    
    async def get_guild(self, guild_id: int) -> Optional[Dict]:
        """Get guild configuration"""
        async with self.conn.execute(
            "SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def update_guild_prefix(self, guild_id: int, prefix: str):
        """Update guild command prefix"""
        await self.conn.execute(
            "UPDATE guilds SET prefix = ? WHERE guild_id = ?",
            (prefix, guild_id)
        )
        await self.conn.commit()
    
    # Moderation methods
    async def log_moderation_action(self, guild_id: int, user_id: int, 
                                   moderator_id: int, action: str, reason: str):
        """Log moderation action"""
        await self.conn.execute(
            """INSERT INTO moderation_logs 
               (guild_id, user_id, moderator_id, action, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, user_id, moderator_id, action, reason)
        )
        await self.conn.commit()
    
    async def log_deleted_message(self, guild_id: int, channel_id: int,
                                  user_id: int, content: str):
        """Log deleted message"""
        await self.conn.execute(
            """INSERT INTO deleted_messages 
               (guild_id, channel_id, user_id, message_content)
               VALUES (?, ?, ?, ?)""",
            (guild_id, channel_id, user_id, content)
        )
        await self.conn.commit()
    
    async def add_warning(self, guild_id: int, user_id: int, 
                         moderator_id: int, reason: str):
        """Add warning to user"""
        await self.conn.execute(
            """INSERT INTO user_warnings 
               (guild_id, user_id, moderator_id, reason)
               VALUES (?, ?, ?, ?)""",
            (guild_id, user_id, moderator_id, reason)
        )
        await self.conn.commit()
    
    async def get_warnings(self, guild_id: int, user_id: int) -> List[Dict]:
        """Get user warnings"""
        async with self.conn.execute(
            """SELECT * FROM user_warnings 
               WHERE guild_id = ? AND user_id = ?
               ORDER BY timestamp DESC""",
            (guild_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Survey methods
    async def create_survey(self, guild_id: int, creator_id: int,
                           title: str, description: str, 
                           questions: List[Dict]) -> int:
        """Create new survey"""
        cursor = await self.conn.execute(
            """INSERT INTO surveys 
               (guild_id, creator_id, title, description, questions)
               VALUES (?, ?, ?, ?, ?)""",
            (guild_id, creator_id, title, description, json.dumps(questions))
        )
        await self.conn.commit()
        return cursor.lastrowid
    
    async def get_survey(self, survey_id: int) -> Optional[Dict]:
        """Get survey by ID"""
        async with self.conn.execute(
            "SELECT * FROM surveys WHERE survey_id = ?", (survey_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                survey = dict(row)
                survey['questions'] = json.loads(survey['questions'])
                return survey
            return None
    
    async def get_active_surveys(self, guild_id: int) -> List[Dict]:
        """Get all active surveys for guild"""
        async with self.conn.execute(
            """SELECT * FROM surveys 
               WHERE guild_id = ? AND active = 1
               ORDER BY created_at DESC""",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            surveys = []
            for row in rows:
                survey = dict(row)
                survey['questions'] = json.loads(survey['questions'])
                surveys.append(survey)
            return surveys
    
    async def submit_survey_response(self, survey_id: int, user_id: int,
                                    answers: List[str]):
        """Submit survey response"""
        await self.conn.execute(
            """INSERT INTO survey_responses 
               (survey_id, user_id, answers)
               VALUES (?, ?, ?)""",
            (survey_id, user_id, json.dumps(answers))
        )
        await self.conn.commit()
    
    async def get_survey_responses(self, survey_id: int) -> List[Dict]:
        """Get all responses for survey"""
        async with self.conn.execute(
            """SELECT * FROM survey_responses 
               WHERE survey_id = ?
               ORDER BY submitted_at DESC""",
            (survey_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            responses = []
            for row in rows:
                response = dict(row)
                response['answers'] = json.loads(response['answers'])
                responses.append(response)
            return responses
    
    async def close_survey(self, survey_id: int):
        """Close survey"""
        await self.conn.execute(
            "UPDATE surveys SET active = 0 WHERE survey_id = ?",
            (survey_id,)
        )
        await self.conn.commit()
    
    # Auto-response methods
    async def add_auto_response(self, guild_id: int, trigger: str, response: str):
        """Add auto-response"""
        await self.conn.execute(
            """INSERT INTO auto_responses (guild_id, trigger, response)
               VALUES (?, ?, ?)""",
            (guild_id, trigger.lower(), response)
        )
        await self.conn.commit()
    
    async def get_auto_responses(self, guild_id: int) -> List[Dict]:
        """Get all auto-responses for guild"""
        async with self.conn.execute(
            """SELECT * FROM auto_responses 
               WHERE guild_id = ? AND enabled = 1""",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def delete_auto_response(self, response_id: int):
        """Delete auto-response"""
        await self.conn.execute(
            "DELETE FROM auto_responses WHERE id = ?", (response_id,)
        )
        await self.conn.commit()
    
    # Scheduled messages methods
    async def add_scheduled_message(self, guild_id: int, channel_id: int,
                                   content: str, cron_expression: str):
        """Add scheduled message"""
        await self.conn.execute(
            """INSERT INTO scheduled_messages 
               (guild_id, channel_id, message_content, cron_expression)
               VALUES (?, ?, ?, ?)""",
            (guild_id, channel_id, content, cron_expression)
        )
        await self.conn.commit()
    
    async def get_scheduled_messages(self, guild_id: int) -> List[Dict]:
        """Get all scheduled messages for guild"""
        async with self.conn.execute(
            """SELECT * FROM scheduled_messages 
               WHERE guild_id = ? AND enabled = 1""",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # Analytics methods
    async def log_analytics_event(self, guild_id: int, event_type: str, 
                                  event_data: Dict):
        """Log analytics event"""
        await self.conn.execute(
            """INSERT INTO analytics (guild_id, event_type, event_data)
               VALUES (?, ?, ?)""",
            (guild_id, event_type, json.dumps(event_data))
        )
        await self.conn.commit()
    
    async def get_analytics(self, guild_id: int, event_type: str = None,
                           days: int = 30) -> List[Dict]:
        """Get analytics data"""
        query = """SELECT * FROM analytics 
                   WHERE guild_id = ? 
                   AND timestamp >= datetime('now', ?)"""
        params = [guild_id, f'-{days} days']
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY timestamp DESC"
        
        async with self.conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            analytics = []
            for row in rows:
                event = dict(row)
                event['event_data'] = json.loads(event['event_data'])
                analytics.append(event)
            return analytics
