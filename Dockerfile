FROM python:3.11-slim

WORKDIR /app

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 디렉토리 생성
RUN mkdir -p cogs

# 실행 권한 설정
RUN chmod +x main.py

# 실행
CMD ["python", "main.py"]