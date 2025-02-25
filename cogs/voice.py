import discord
from discord import app_commands
from discord.ext import commands
import logging

# 로깅 설정
logger = logging.getLogger("voice")

class VoiceCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def create_voice_embed(self, title: str, description: str, color: discord.Color) -> discord.Embed:
        """음성 채널 관련 임베드 생성 헬퍼 함수"""
        embed = discord.Embed(title=title, description=description, color=color)
        return embed
    
    @app_commands.command(name="입장", description="음성 채널에 입장합니다")
    async def join(self, interaction: discord.Interaction):
        """음성 채널 입장 명령어"""
        try:
            # 사용자가 음성 채널에 없을때
            if not interaction.user.voice:
                embed = await self.create_voice_embed(
                    "⚠️ 음성 채널 입장 실패",
                    f"{interaction.user.mention}님, 먼저 음성 채널에 입장해주세요!",
                    discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
                return

            channel = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client

            # 봇이 이미 음성 채널에 있을때
            if voice_client:
                if voice_client.channel == channel:
                    embed = await self.create_voice_embed(
                        "ℹ️ 알림",
                        f"멜로디가 이미 {channel.mention} 채널에 있습니다!",
                        discord.Color.blue()
                    )
                    await interaction.response.send_message(embed=embed)
                    return

                await voice_client.move_to(channel)
                embed = await self.create_voice_embed(
                    "✅ 채널 이동 완료",
                    f"{channel.mention} 채널로 이동했습니다!",
                    discord.Color.green()
                )
                await interaction.response.send_message(embed=embed)
                return

            # 새로운 채널 입장
            await channel.connect()
            embed = await self.create_voice_embed(
                "✅ 채널 입장 완료",
                f"{channel.mention} 채널에 입장했습니다!",
                discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            logger.info(f"음성 채널 {channel.name} 입장 완료")

        except Exception as e:
            logger.error(f"음성 채널 입장 중 오류 발생: {e}")
            embed = await self.create_voice_embed(
                "❌ 오류 발생",
                f"채널 입장 중 오류가 발생했습니다: {str(e)}",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="퇴장", description="음성 채널에서 퇴장합니다")
    async def leave(self, interaction: discord.Interaction):
        try:
            if not interaction.guild.voice_client:
                embed = await self.create_voice_embed(
                    "ℹ️ 알림",
                    "음성 채널에 입장해있지 않습니다!",
                    discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                return

            await interaction.guild.voice_client.disconnect()
            embed = await self.create_voice_embed(
                "👋 채널 퇴장 완료",
                "음성 채널에서 퇴장했습니다!",
                discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            logger.info(f"음성 채널 퇴장 완료")

        except Exception as e:
            logger.error(f"음성 채널 퇴장 중 오류 발생: {e}")
            embed = await self.create_voice_embed(
                "❌ 오류 발생",
                f"채널 퇴장 중 오류가 발생했습니다: {str(e)}",
                discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceCommands(bot))