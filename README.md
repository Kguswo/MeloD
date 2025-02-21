# MeloD - 디스코드 뮤직 봇
![MeloD_Logo_img](assets/MeloD_Logo.png)
디스코드 서버를 위한 음악 재생 봇입니다.

## 기능
- 유튜브 URL 또는 검색어로 음악 재생
- 재생 목록 관리
- 기본적인 음악 제어 (일시정지, 재개, 스킵)

## 설치 방법

1. 저장소 클론
   
    `git clone https://github.com/유저명/MeloD.git
cd MeloD`

2. 필요한 패키지 설치
   
    `pip install -r requirements.txt`

3. FFmpeg 설치 (음악 스트리밍에 필요)
- Windows: https://ffmpeg.org/download.html
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

4. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용 추가: `DISCORD_TOKEN=your_discord_token_here`

5. 봇 실행
    `python main.py`

## 명령어
- `/도움말` - 사용 가능한 명령어 목록
- `/재생 [URL 또는 검색어]` - 음악 재생
- `/일시정지` - 현재 곡 일시정지
- `/다시재생` - 일시정지된 곡 재생 재개
- `/이전` - 이전 곡으로 이동
- `/다음` - 다음 곡으로 이동
- `/재생목록` - 재생목록 큐 보기
- `/종료` - 봇 연결 종료