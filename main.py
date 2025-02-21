import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print('로그인 완료')
    print(f'{bot.user}에 로그인하였습니다.')
    print(f'ID: {bot.user.name}')
    await bot.change_presence(
        status=discord.Status.online, 
        activity=discord.Game('MeloD 테스트 중 | /도움말')
    )

# 봇 실행
if __name__ == "__main__":
    bot.run(TOKEN)