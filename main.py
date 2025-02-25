import discord
from discord import app_commands
from discord.ext import commands
from discord import Embed, Color
import asyncio
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
import logging
from database import Database

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot")

# 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 봇 설정
class AttendanceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        self.db = None
        
    async def setup_hook(self):
        # 데이터베이스 연결
        from database import Database
        logger.info("데이터베이스 연결 중...")
        self.db = Database()
        await self.db.init_db()
        logger.info("데이터베이스 연결 완료")
        
        # Cog 로드
        logger.info("명령어 모듈 로드 중...")
        await self.load_extension("cogs.attendance")  # 출석체크 명령어
        await self.load_extension("cogs.voice")       # 음성 채널 명령어
        logger.info("명령어 모듈 로드 완료")
        
        # 슬래시 명령어 등록
        try:
            logger.info("슬래시 명령어 동기화 중...")
            synced = await self.tree.sync()
            logger.info(f"동기화된 슬래시 명령어: {len(synced)} 개")
        except Exception as e:
            logger.error(f"슬래시 명령어 동기화 실패: {e}")
        
    async def on_ready(self):
        logger.info(f'로그인 완료: {self.user.name} (ID: {self.user.id})')
        await self.change_presence(
            status=discord.Status.online, 
            activity=discord.Game('MeloD 테스트 중 | /도움말')
        )
        
    async def close(self):
        # 종료 시 데이터베이스 연결 닫기
        if self.db:
            logger.info("데이터베이스 연결 종료 중...")
            await self.db.close()
            logger.info("데이터베이스 연결 종료 완료")
        await super().close()

# 기본 명령어
@discord.app_commands.command(name="핑", description="봇의 지연 시간을 확인합니다")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'🏓 퐁! {round(interaction.client.latency * 1000)}ms')

@discord.app_commands.command(name="테스트", description="봇이 정상 작동하는지 테스트합니다")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention}, 테스트가 정상적으로 작동합니다!")

# 명령어
@discord.app_commands.command(name="도움말", description="MeloD 봇의 명령어 목록을 보여줍니다")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵   MeloD 뮤직봇 도움말",
        description="음악과 함께하는 즐거운 시간!",
        color=discord.Color.blue()
    )
    
    # 기본 명령어
    basic = """
    `/도움말` - 이 도움말을 표시합니다
    `/help` - 상세 명령어 도움말을 표시합니다
    `/핑` - 봇의 응답 시간을 체크합니다
    `/출첵` - 출석 체크를 합니다.
    """
    embed.add_field(name="🤖  기본 명령어", value=basic, inline=False)

    # 음성 채널 명령어
    voice_channel = """
    `/입장` - 음성 채널에 입장합니다
    `/퇴장` - 음성 채널에서 퇴장합니다
    """
    embed.add_field(name="📺  음성 채널 명령어", value=voice_channel, inline=False)

    
    # 음악 명령어
    music = """
    `/재생 [노래이름/URL]` - 음악을 재생합니다
    `/일시정지` - 재생 중인 음악을 일시정지합니다
    `/다시재생` - 일시정지된 음악을 다시 재생합니다
    `/이전` - 이전 음악으로 돌아갑니다.
    `/다음` - 다음 음악으로 넘어갑니다.
    """
    embed.add_field(name="🎵  음악 명령어", value=music, inline=False)

    # 재생목록 명령어
    playlist = """
    `/목록` - 현재 재생목록을 보여줍니다
    `/나가` - 음성 채널에서 나갑니다
    """
    embed.add_field(name="📋  재생목록 관리", value=playlist, inline=False)
    
    embed.set_footer(text="자세한 명령어 사용법은 /help를 입력해주세요!")
    
    await interaction.response.send_message(embed=embed)

# 봇 실행
async def main():
    bot = AttendanceBot()
    bot.tree.add_command(ping)
    bot.tree.add_command(test)
    bot.tree.add_command(help_command)

    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())