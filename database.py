import asyncpg
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import pytz
import asyncio

# 로깅 설정
logger = logging.getLogger("database")

# 환경 변수 로드
load_dotenv()
DB_HOST = os.getenv('DB_HOST')  # Docker Compose에서는 서비스 이름으로 연결
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

class Database:
    def __init__(self):
        self.pool = None
    
    async def init_db(self):
        """데이터베이스 초기화 및 테이블 생성"""
        # 데이터베이스 연결이 준비될 때까지 재시도
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                logger.info(f"PostgreSQL 연결 시도 중... (시도 {retry_count+1}/{max_retries})")
                self.pool = await asyncpg.create_pool(
                    host=DB_HOST,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD
                )
                logger.info("PostgreSQL 연결 성공")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"PostgreSQL 연결 실패: {e}")
                if retry_count >= max_retries:
                    logger.error("최대 재시도 횟수 초과. 데이터베이스 연결 실패")
                    raise
                await asyncio.sleep(5)  # 5초 후 재시도
        
        # 테이블 생성
        async with self.pool.acquire() as conn:
            
            # 사용자 통계 테이블
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    display_name TEXT,
                    current_streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0,
                    total_days INTEGER DEFAULT 0,
                    last_attendance_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 출석 테이블
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT REFERENCES user_stats(user_id),
                    attendance_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, attendance_date)
                )
            ''')
            
            logger.info("데이터베이스 테이블 생성 완료")
    
    async def close(self):
        """데이터베이스 연결 종료"""
        if self.pool:
            await self.pool.close()
    
    async def check_attendance(self, user_id, date):
        """특정 날짜의 출석 여부 확인"""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                'SELECT * FROM attendance WHERE user_id = $1 AND attendance_date = $2', 
                user_id, date
            )
            return record is not None
    
    async def mark_attendance(self, user_id, user_name, display_name, date_str):
        """출석 체크 및 통계 업데이트"""
        # 날짜 문자열을 날짜 객체로 변환
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 이미 출석했는지 확인
        if await self.check_attendance(user_id, date_obj):
            return False, None
        
        async with self.pool.acquire() as conn:
            # 트랜잭션 시작
            async with conn.transaction():
                # 사용자 존재 여부 확인
                user = await conn.fetchrow(
                    'SELECT * FROM user_stats WHERE user_id = $1', user_id
                )

                if user:
                    # 사용자 정보 업데이트 (이름 변경될 가능성 있으므로)
                    await conn.execute(
                        'UPDATE user_stats SET user_name = $1, display_name = $2 WHERE user_id = $3',
                        user_name, display_name, user_id
                    )
                    
                    # 어제 출석했는지 확인 (연속 출석)
                    yesterday = (date_obj - timedelta(days=1))
                    yesterday_attendance = await self.check_attendance(user_id, yesterday)
                    
                    if yesterday_attendance:
                        # 연속 출석 증가
                        current_streak = user['current_streak'] + 1
                    else:
                        # 연속 출석 초기화
                        current_streak = 1
                        
                    # 최대 연속 출석 업데이트
                    max_streak = max(current_streak, user['max_streak'])
                    total_days = user['total_days'] + 1
                    
                    # 사용자 통계 업데이트
                    await conn.execute('''
                        UPDATE user_stats 
                        SET current_streak = $1, max_streak = $2, total_days = $3, last_attendance_date = $4
                        WHERE user_id = $5
                    ''', current_streak, max_streak, total_days, date_obj, user_id)
                else:
                    # 새 사용자 등록
                    await conn.execute('''
                        INSERT INTO user_stats 
                        (user_id, user_name, display_name, current_streak, max_streak, total_days, last_attendance_date)
                        VALUES ($1, $2, $3, 1, 1, 1, $4)
                    ''', user_id, user_name, display_name, date_obj)
                    
                    current_streak = 1
                    max_streak = 1
                    total_days = 1

                # 출석 기록 추가
                await conn.execute(
                    'INSERT INTO attendance (user_id, attendance_date) VALUES ($1, $2)',
                    user_id, date_obj
                )


        return True, {
            'current_streak': current_streak,
            'max_streak': max_streak,
            'total_days': total_days
        }
    
    async def get_user_stats(self, user_id):
        """사용자 출석 통계 가져오기"""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                '''SELECT user_name, display_name, current_streak, max_streak, total_days, 
                   last_attendance_date FROM user_stats WHERE user_id = $1''',
                user_id
            )
            
            if not record:
                return None
                
            return {
                'user_name': record['user_name'],
                'display_name': record['display_name'],
                'current_streak': record['current_streak'],
                'max_streak': record['max_streak'],
                'total_days': record['total_days'],
                'last_attendance_date': record['last_attendance_date'].strftime('%Y-%m-%d') if record['last_attendance_date'] else None
            }
            
    async def get_monthly_attendance(self, user_id, year, month):
        """해당 월의 출석 기록 가져오기"""
        async with self.pool.acquire() as conn:
            # 해당 월의 첫날과 마지막날
            first_day = datetime(year, month, 1).date()
            if month == 12:
                last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            records = await conn.fetch(
                'SELECT attendance_date FROM attendance WHERE user_id = $1 AND attendance_date BETWEEN $2 AND $3 ORDER BY attendance_date',
                user_id, first_day, last_day
            )
            
            return [record['attendance_date'].strftime('%Y-%m-%d') for record in records]
            
    async def get_server_stats(self, guild_id):
        """서버 전체 출석 통계"""
        async with self.pool.acquire() as conn:
            # 오늘 출석한 사용자 수
            today = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
            today_obj = datetime.strptime(today, '%Y-%m-%d').date()
            
            today_count = await conn.fetchval(
                'SELECT COUNT(DISTINCT user_id) FROM attendance WHERE attendance_date = $1',
                today_obj
            )
            
            # 전체 사용자 수
            total_users = await conn.fetchval(
                'SELECT COUNT(DISTINCT user_id) FROM user_stats'
            )
            
            # 최장 연속 출석자
            top_streak = await conn.fetchrow(
                'SELECT user_id, user_name, display_name, max_streak FROM user_stats ORDER BY max_streak DESC LIMIT 1'
            )
            
            # 결과 값이 None인 경우 기본값으로 설정
            if today_count is None:
                today_count = 0
            if total_users is None:
                total_users = 0
            if top_streak is None:
                top_streak = {'user_id': None, 'user_name': None, 'display_name': None, 'max_streak': 0}
                
            return {
                'today_attendance': today_count,
                'total_users': total_users,
                'top_streak': top_streak
            }
        
    async def get_rankings(self):
        """출석 랭킹 데이터 가져오기"""
        async with self.pool.acquire() as conn:
            # 연속 출석 랭킹
            streak_ranks = await conn.fetch(
                '''SELECT user_id, user_name, display_name, current_streak 
                   FROM user_stats 
                   ORDER BY current_streak DESC, total_days DESC 
                   LIMIT 5'''
            )
            
            # 최대 연속 출석 랭킹
            max_streak_ranks = await conn.fetch(
                '''SELECT user_id, user_name, display_name, max_streak 
                   FROM user_stats 
                   ORDER BY max_streak DESC, total_days DESC 
                   LIMIT 5'''
            )
            
            # 총 출석일 랭킹
            total_ranks = await conn.fetch(
                '''SELECT user_id, user_name, display_name, total_days 
                   FROM user_stats 
                   ORDER BY total_days DESC, max_streak DESC 
                   LIMIT 5'''
            )
            
            return {
                'streak_ranks': streak_ranks,
                'max_streak_ranks': max_streak_ranks,
                'total_ranks': total_ranks
            }