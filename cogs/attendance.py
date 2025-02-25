import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import logging

# 로깅 설정
logger = logging.getLogger("attendance")

class AttendanceCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db
    
    @app_commands.command(name='출첵', description="출석체크")
    async def check_attendance(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # 한국 시간으로 설정
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).strftime('%Y-%m-%d')
        
        try:
            success, stats = await self.db.mark_attendance(user_id, today)
            
            if not success:
                await interaction.response.send_message(f'{interaction.user.mention} 이미 오늘은 출석체크를 하셨어요!')
                return
            
            embed = discord.Embed(
                title="✅ 출석체크 완료!",
                description=f"{interaction.user.mention}님이 출석체크 하셨습니다!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📊 출석 정보", 
                value=f"🔥 연속 출석: {stats['current_streak']}일\n"
                      f"🏆 최대 연속 출석: {stats['max_streak']}일\n"
                      f"📅 총 출석: {stats['total_days']}일", 
                inline=False
            )
            
            # 서버 통계 추가
            server_stats = await self.db.get_server_stats(interaction.guild.id)
            if server_stats['today_attendance'] > 0:
                embed.add_field(
                    name="🌍 서버 통계",
                    value=f"오늘 출석: {server_stats['today_attendance']}명\n"
                          f"전체 등록: {server_stats['total_users']}명",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"사용자 {user_id} 출석체크 완료. 연속 출석: {stats['current_streak']}일")
        except Exception as e:
            logger.error(f"출석체크 중 오류 발생: {e}")
            await interaction.response.send_message("출석체크 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

    @app_commands.command(name="출석정보", description="출석 정보를 확인합니다")
    @app_commands.describe(member="확인할 멤버를 선택하세요 (선택사항)")
    async def attendance_info(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user
        
        user_id = str(member.id)
        
        try:
            stats = await self.db.get_user_stats(user_id)
            
            if not stats:
                await interaction.response.send_message(f'{member.mention}님의 출석 기록이 없습니다.')
                return
            
            embed = discord.Embed(
                title=f"📊 {member.name}님의 출석 정보",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="출석 통계", 
                value=f"🔥 현재 연속 출석: {stats['current_streak']}일\n"
                      f"🏆 최대 연속 출석: {stats['max_streak']}일\n"
                      f"📅 총 출석 일수: {stats['total_days']}일\n"
                      f"📌 마지막 출석일: {stats['last_attendance_date']}", 
                inline=False
            )
            
            # 한국 시간 기준 다음 출석 가능 시간 계산
            kst = pytz.timezone('Asia/Seoul')
            last_attendance = datetime.strptime(stats['last_attendance_date'], '%Y-%m-%d').replace(tzinfo=kst)
            now = datetime.now(kst)
            
            # 마지막 출석이 오늘이면, 내일 자정 이후부터 가능
            if last_attendance.date() == now.date():
                next_attendance = datetime.combine(now.date() + timedelta(days=1), 
                                                 datetime.min.time()).replace(tzinfo=kst)
                time_until = next_attendance - now
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed.add_field(
                    name="⏰ 다음 출석 가능 시간", 
                    value=f"{hours}시간 {minutes}분 후", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"사용자 {user_id}의 출석 정보 조회 완료")
        except Exception as e:
            logger.error(f"출석 정보 조회 중 오류 발생: {e}")
            await interaction.response.send_message("출석 정보 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

    @app_commands.command(name="월간출석", description="이번 달 출석 현황을 확인합니다")
    async def monthly_attendance(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        try:
            # 한국 시간으로 현재 연도와 월 가져오기
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            year, month = now.year, now.month
            
            # 이번 달의 첫날과 마지막 날
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # 이번 달 출석 일수 계산
            attendance_days = await self.db.get_monthly_attendance(user_id, year, month)
            
            if not attendance_days:
                await interaction.response.send_message(f'{interaction.user.mention}님은 이번 달 출석 기록이 없습니다.')
                return
            
            # 달력 형태로 출석 현황 표시
            calendar_str = f"📅 {year}년 {month}월 출석 현황\n\n"
            calendar_str += "일 월 화 수 목 금 토\n"
            
            # 1일의 요일 계산 (0:월 ~ 6:일)
            first_weekday = first_day.weekday()
            # 파이썬은 월요일이 0이므로 일요일을 0으로 맞추기 위해 조정
            first_weekday = (first_weekday + 1) % 7
            
            # 달력 첫 줄 앞부분 공백 채우기
            calendar_str += "   " * first_weekday
            
            for day in range(1, last_day.day + 1):
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # 출석한 날이면 ✓ 표시
                if date_str in attendance_days:
                    calendar_str += " ✓ "
                else:
                    calendar_str += f" {day:2d} "
                
                # 토요일이면 줄바꿈
                if (first_weekday + day) % 7 == 0:
                    calendar_str += "\n"
            
            embed = discord.Embed(
                title=f"📊 {interaction.user.name}님의 {month}월 출석 현황",
                description=f"```{calendar_str}```",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="통계", 
                value=f"이번 달 출석일: {len(attendance_days)}일 / {last_day.day}일", 
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"사용자 {user_id}의 월간 출석 현황 조회 완료")
        except Exception as e:
            logger.error(f"월간 출석 현황 조회 중 오류 발생: {e}")
            await interaction.response.send_message("월간 출석 현황 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)
            
    @app_commands.command(name="출석랭킹", description="서버 출석 랭킹을 확인합니다")
    async def attendance_ranking(self, interaction: discord.Interaction):
        try:
            async with self.db.pool.acquire() as conn:
                # 연속 출석 랭킹
                streak_ranks = await conn.fetch(
                    'SELECT user_id, current_streak FROM user_stats ORDER BY current_streak DESC LIMIT 5'
                )
                
                # 최대 연속 출석 랭킹
                max_streak_ranks = await conn.fetch(
                    'SELECT user_id, max_streak FROM user_stats ORDER BY max_streak DESC LIMIT 5'
                )
                
                # 총 출석일 랭킹
                total_ranks = await conn.fetch(
                    'SELECT user_id, total_days FROM user_stats ORDER BY total_days DESC LIMIT 5'
                )
            
            embed = discord.Embed(
                title=f"🏆 {interaction.guild.name} 출석 랭킹",
                color=discord.Color.gold()
            )
            
            # 연속 출석 랭킹
            if streak_ranks:
                streak_txt = ""
                for i, rank in enumerate(streak_ranks):
                    user = self.bot.get_user(int(rank['user_id']))
                    if user:
                        streak_txt += f"{i+1}. {user.name}: {rank['current_streak']}일\n"
                    else:
                        streak_txt += f"{i+1}. 알 수 없는 사용자: {rank['current_streak']}일\n"
                
                embed.add_field(
                    name="🔥 연속 출석 랭킹",
                    value=streak_txt,
                    inline=False
                )
            
            # 최대 연속 출석 랭킹
            if max_streak_ranks:
                max_streak_txt = ""
                for i, rank in enumerate(max_streak_ranks):
                    user = self.bot.get_user(int(rank['user_id']))
                    if user:
                        max_streak_txt += f"{i+1}. {user.name}: {rank['max_streak']}일\n"
                    else:
                        max_streak_txt += f"{i+1}. 알 수 없는 사용자: {rank['max_streak']}일\n"
                
                embed.add_field(
                    name="🏅 최대 연속 출석 랭킹",
                    value=max_streak_txt,
                    inline=False
                )
            
            # 총 출석일 랭킹
            if total_ranks:
                total_txt = ""
                for i, rank in enumerate(total_ranks):
                    user = self.bot.get_user(int(rank['user_id']))
                    if user:
                        total_txt += f"{i+1}. {user.name}: {rank['total_days']}일\n"
                    else:
                        total_txt += f"{i+1}. 알 수 없는 사용자: {rank['total_days']}일\n"
                
                embed.add_field(
                    name="📅 총 출석일 랭킹",
                    value=total_txt,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info("출석 랭킹 조회 완료")
        except Exception as e:
            logger.error(f"출석 랭킹 조회 중 오류 발생: {e}")
            await interaction.response.send_message("출석 랭킹 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AttendanceCommands(bot))