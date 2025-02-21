import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta

# 환경 변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# DB 초기화
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            user_id TEXT,
            attendance_date TEXT,
            streak INTEGER DEFAULT 1,
            total_days INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, attendance_date)
        )
    ''')
    conn.commit
    conn.close

@bot.event
async def on_ready():
    init_db()
    print('로그인 완료')
    print(f'{bot.user}에 로그인하였습니다.')
    print(f'ID: {bot.user.name}')
    await bot.change_presence(
        status=discord.Status.online, 
        activity=discord.Game('MeloD 테스트 중 | /도움말')
    )

@bot.command(name='핑')
async def ping(ctx):
    await ctx.send(f'🏓 퐁! {round(bot.latency * 1000)}ms')

@bot.command(name='테스트')
async def test(ctx):
    await ctx.send(f"{ctx.author.mention}, 테스트가 정상적으로 작동합니다!")

@bot.command(name='출첵', aliases=['출석체크'])
async def check_attendance(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now().strftime('%Y-%m-%d')

    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()

    # 오늘 출석했는지 확인하기
    c.execute('SELECT * FROM attendance WHERE user_id = ? AND attendance_date = ?',(user_id, today))
    if c.fetchone():
        await ctx.send(f'{ctx.author.mention} 이미 오늘은 출석체크를 하셨어요!')
        conn.close()
        return
    
    # 연속 출석 확인하기
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    c.execute('SELECT streak, total_days FROM attendance WHERE user_id = ? ORDER BY attendance_date DESC LIMIT 1', (user_id,))
    result = c.fetchone()

    if result:
        c.execute('SELECT * FROM attendance WHERE user_id = ? AND attendance_date = ?', (user_id, yesterday))
        
        if c.fetchone(): # 어제 출석했으면
            streak = result[0] + 1
            total_days = result[1] + 1
        else: # 어제 출석 안했으면
            streak = 1
            total_days = result[1] + 1
    
    # 첫 출석
    else:
        streak = 1
        total_days = 1

    c.execute('''
        INSERT INTO attendance (user_id, attend_date, streak, total_days)
        VALUES (?, ?, ?, ?)
    ''', (user_id, today, streak, total_days))

    conn.commit()

    embed = discord.Embed(
        title="✅ 출석체크 완료!",
        description=f"{ctx.author.mention}님이 출석체크 하셨습니다!",
        color=discord.Color.green()
    )
    embed.add_field(name="📊 출석 정보", value=f"🔥 연속 출석: {streak}일\n📅 총 출석: {total_days}일", inline=False)

    await ctx.send(embed=embed)
    conn.close()

@bot.command(name='출석정보')
async def attendance_info(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    user_id = str(member.id)
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    
    # 최근 출석 정보 조회
    c.execute('''
        SELECT streak, total_days, attend_date 
        FROM attendance 
        WHERE user_id = ? 
        ORDER BY attend_date DESC 
        LIMIT 1
    ''', (user_id,))
    result = c.fetchone()
    
    if not result:
        await ctx.send(f'{member.mention}님의 출석 기록이 없습니다.')
        conn.close()
        return
    
    streak, total_days, last_date = result

    embed = discord.Embed(
        title=f"📊 {member.name}님의 출석 정보",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="출석 통계", 
        value=f"🔥 현재 연속 출석: {streak}일\n"
              f"📅 총 출석 일수: {total_days}일\n"
              f"📌 마지막 출석일: {last_date}", 
        inline=False
    )

    await ctx.send(embed=embed)
    conn.close()

# 봇 실행
if __name__ == "__main__":
    bot.run(TOKEN)