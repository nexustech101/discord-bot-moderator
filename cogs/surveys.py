import discord
from discord.ext import commands
from typing import List, Dict, Optional
import asyncio

from config import Config, EMBED_COLORS
from utils.helpers import *
from utils.logger import setup_logger

logger = setup_logger("Surveys")

class SurveyBuilder:
    """Interactive survey builder"""
    
    def __init__(self, ctx, title: str):
        self.ctx = ctx
        self.title = title
        self.description = ""
        self.questions = []
    
    async def add_question(self, question_text: str, question_type: str = "text"):
        """Add a question to the survey"""
        self.questions.append({
            "text": question_text,
            "type": question_type,
            "options": []
        })
    
    async def build(self):
        """Interactive survey building process"""
        await self.ctx.send(f"📋 Building survey: **{self.title}**")
        
        # Get description
        await self.ctx.send("Enter a description for your survey (or 'skip'):")
        
        try:
            msg = await self.ctx.bot.wait_for(
                'message',
                check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel,
                timeout=60.0
            )
            if msg.content.lower() != 'skip':
                self.description = msg.content
        except asyncio.TimeoutError:
            await self.ctx.send("⏱️ Survey creation timed out.")
            return None
        
        # Add questions
        question_count = 0
        while question_count < Config.MAX_SURVEY_QUESTIONS:
            await self.ctx.send(f"**Question {question_count + 1}:** Enter your question (or 'done' to finish):")
            
            try:
                msg = await self.ctx.bot.wait_for(
                    'message',
                    check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel,
                    timeout=120.0
                )
                
                if msg.content.lower() == 'done':
                    break
                
                question_text = msg.content
                
                # Ask for question type
                await self.ctx.send(
                    "Select question type:\n"
                    "1️⃣ Text (short answer)\n"
                    "2️⃣ Multiple Choice\n"
                    "3️⃣ Scale (1-10)\n"
                    "4️⃣ Yes/No"
                )
                
                type_msg = await self.ctx.bot.wait_for(
                    'message',
                    check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel,
                    timeout=60.0
                )
                
                question_type = "text"
                options = []
                
                if type_msg.content == "2":
                    question_type = "mcq"
                    await self.ctx.send("Enter options separated by commas (e.g., Option A, Option B, Option C):")
                    
                    options_msg = await self.ctx.bot.wait_for(
                        'message',
                        check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel,
                        timeout=60.0
                    )
                    options = [opt.strip() for opt in options_msg.content.split(',')]
                
                elif type_msg.content == "3":
                    question_type = "scale"
                    options = list(range(1, 11))
                
                elif type_msg.content == "4":
                    question_type = "yes_no"
                    options = ["Yes", "No"]
                
                self.questions.append({
                    "text": question_text,
                    "type": question_type,
                    "options": options
                })
                
                question_count += 1
                await self.ctx.send(f"✅ Question {question_count} added!")
                
            except asyncio.TimeoutError:
                await self.ctx.send("⏱️ Survey creation timed out.")
                break
        
        if not self.questions:
            await self.ctx.send("❌ Survey must have at least one question.")
            return None
        
        return {
            "title": self.title,
            "description": self.description,
            "questions": self.questions
        }

class Surveys(commands.Cog):
    """Survey and feedback management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_surveys = {}  # survey_id -> message_id mapping
    
    @commands.command(name="createsurvey", aliases=["newsurvey"])
    @commands.has_permissions(manage_guild=True)
    async def create_survey(self, ctx, *, title: str):
        """Create a new survey"""
        builder = SurveyBuilder(ctx, title)
        survey_data = await builder.build()
        
        if not survey_data:
            return
        
        # Save to database
        survey_id = await self.bot.db.create_survey(
            ctx.guild.id,
            ctx.author.id,
            survey_data['title'],
            survey_data['description'],
            survey_data['questions']
        )
        
        # Create survey embed
        embed = create_embed(
            title=f"📊 {survey_data['title']}",
            description=survey_data['description'] or "No description provided",
            color_key="survey"
        )
        
        embed.add_field(
            name="Questions",
            value=f"{len(survey_data['questions'])} questions",
            inline=True
        )
        
        embed.add_field(
            name="Survey ID",
            value=f"`{survey_id}`",
            inline=True
        )
        
        embed.set_footer(text=f"Use !takesurvey {survey_id} to participate")
        
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} created survey '{title}' (ID: {survey_id}) in {ctx.guild.name}")
    
    @commands.command(name="takesurvey", aliases=["survey"])
    async def take_survey(self, ctx, survey_id: int):
        """Take a survey"""
        # Get survey from database
        survey = await self.bot.db.get_survey(survey_id)
        
        if not survey:
            await ctx.send("❌ Survey not found.")
            return
        
        if not survey['active']:
            await ctx.send("❌ This survey is no longer active.")
            return
        
        # Check if user already responded
        responses = await self.bot.db.get_survey_responses(survey_id)
        if any(r['user_id'] == ctx.author.id for r in responses):
            await ctx.send("❌ You have already taken this survey.")
            return
        
        # Send survey in DMs
        try:
            await ctx.author.send(f"📊 Starting survey: **{survey['title']}**")
            
            answers = []
            
            for idx, question in enumerate(survey['questions'], 1):
                # Create question embed
                embed = create_embed(
                    title=f"Question {idx}/{len(survey['questions'])}",
                    description=question['text'],
                    color_key="survey"
                )
                
                if question['type'] == 'mcq':
                    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(question['options'])])
                    embed.add_field(name="Options", value=options_text, inline=False)
                    embed.set_footer(text="Reply with the option number")
                
                elif question['type'] == 'scale':
                    embed.set_footer(text="Reply with a number from 1 to 10")
                
                elif question['type'] == 'yes_no':
                    embed.set_footer(text="Reply with 'yes' or 'no'")
                
                else:
                    embed.set_footer(text="Reply with your answer")
                
                await ctx.author.send(embed=embed)
                
                # Wait for answer
                try:
                    answer_msg = await self.bot.wait_for(
                        'message',
                        check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel),
                        timeout=300.0  # 5 minutes per question
                    )
                    
                    answer = answer_msg.content
                    
                    # Validate answer based on question type
                    if question['type'] == 'mcq':
                        try:
                            choice = int(answer) - 1
                            if 0 <= choice < len(question['options']):
                                answer = question['options'][choice]
                            else:
                                await ctx.author.send("❌ Invalid option. Survey cancelled.")
                                return
                        except ValueError:
                            await ctx.author.send("❌ Invalid option. Survey cancelled.")
                            return
                    
                    elif question['type'] == 'scale':
                        try:
                            rating = int(answer)
                            if not (1 <= rating <= 10):
                                await ctx.author.send("❌ Rating must be between 1 and 10. Survey cancelled.")
                                return
                        except ValueError:
                            await ctx.author.send("❌ Invalid rating. Survey cancelled.")
                            return
                    
                    elif question['type'] == 'yes_no':
                        answer_lower = answer.lower()
                        if answer_lower not in ['yes', 'no']:
                            await ctx.author.send("❌ Please answer with 'yes' or 'no'. Survey cancelled.")
                            return
                        answer = "Yes" if answer_lower == "yes" else "No"
                    
                    answers.append(answer)
                    await ctx.author.send("✅ Answer recorded!")
                    
                except asyncio.TimeoutError:
                    await ctx.author.send("⏱️ Survey timed out.")
                    return
            
            # Save responses
            await self.bot.db.submit_survey_response(survey_id, ctx.author.id, answers)
            
            # Send confirmation
            thank_you_embed = success_embed(
                "Survey Complete!",
                f"Thank you for completing **{survey['title']}**!\n\nYour responses have been recorded."
            )
            await ctx.author.send(embed=thank_you_embed)
            
            # Notify in channel
            await ctx.send(f"✅ {ctx.author.mention} Check your DMs to complete the survey!")
            
            logger.info(f"{ctx.author} completed survey {survey_id}")
            
        except discord.Forbidden:
            await ctx.send("❌ I couldn't send you a DM. Please enable DMs from server members.")
    
    @commands.command(name="surveyresults", aliases=["results"])
    @commands.has_permissions(manage_guild=True)
    async def survey_results(self, ctx, survey_id: int):
        """View survey results"""
        survey = await self.bot.db.get_survey(survey_id)
        
        if not survey:
            await ctx.send("❌ Survey not found.")
            return
        
        if survey['guild_id'] != ctx.guild.id:
            await ctx.send("❌ This survey doesn't belong to this server.")
            return
        
        responses = await self.bot.db.get_survey_responses(survey_id)
        
        if not responses:
            await ctx.send("📊 No responses yet for this survey.")
            return
        
        # Create results embed
        embed = create_embed(
            title=f"📊 Results: {survey['title']}",
            description=f"Total Responses: **{len(responses)}**",
            color_key="survey"
        )
        
        # Analyze each question
        for idx, question in enumerate(survey['questions']):
            answers = [r['answers'][idx] for r in responses if len(r['answers']) > idx]
            
            if question['type'] in ['mcq', 'yes_no']:
                # Count occurrences
                from collections import Counter
                counter = Counter(answers)
                result_text = "\n".join([f"{opt}: {count} ({count/len(answers)*100:.1f}%)" 
                                        for opt, count in counter.most_common()])
            
            elif question['type'] == 'scale':
                # Calculate average
                try:
                    numeric_answers = [int(a) for a in answers]
                    average = sum(numeric_answers) / len(numeric_answers)
                    result_text = f"Average: {average:.2f}/10"
                except:
                    result_text = "Unable to calculate"
            
            else:
                # Show first few text responses
                result_text = "\n".join([f"- {a[:50]}..." if len(a) > 50 else f"- {a}" 
                                        for a in answers[:3]])
                if len(answers) > 3:
                    result_text += f"\n... and {len(answers) - 3} more"
            
            embed.add_field(
                name=f"Q{idx+1}: {question['text'][:100]}",
                value=result_text or "No data",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} viewed results for survey {survey_id}")
    
    @commands.command(name="closesurvey")
    @commands.has_permissions(manage_guild=True)
    async def close_survey(self, ctx, survey_id: int):
        """Close a survey"""
        survey = await self.bot.db.get_survey(survey_id)
        
        if not survey:
            await ctx.send("❌ Survey not found.")
            return
        
        if survey['guild_id'] != ctx.guild.id:
            await ctx.send("❌ This survey doesn't belong to this server.")
            return
        
        await self.bot.db.close_survey(survey_id)
        
        embed = success_embed(
            "Survey Closed",
            f"Survey **{survey['title']}** (ID: {survey_id}) is now closed."
        )
        await ctx.send(embed=embed)
        
        logger.info(f"{ctx.author} closed survey {survey_id}")
    
    @commands.command(name="listsurveys")
    async def list_surveys(self, ctx):
        """List all active surveys"""
        surveys = await self.bot.db.get_active_surveys(ctx.guild.id)
        
        if not surveys:
            await ctx.send("📊 No active surveys in this server.")
            return
        
        embed = info_embed(
            "Active Surveys",
            f"Found {len(surveys)} active survey(s)"
        )
        
        for survey in surveys[:10]:  # Limit to 10
            responses = await self.bot.db.get_survey_responses(survey['survey_id'])
            
            embed.add_field(
                name=survey['title'],
                value=f"**ID:** {survey['survey_id']}\n"
                      f"**Questions:** {len(survey['questions'])}\n"
                      f"**Responses:** {len(responses)}\n"
                      f"**Command:** `!takesurvey {survey['survey_id']}`",
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Surveys(bot))
