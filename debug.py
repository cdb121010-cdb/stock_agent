import os
import ccxt
from dotenv import load_dotenv

# 1. 환경변수 로드
load_dotenv()
API_KEY = (os.getenv("BITHUMB_API_KEY") or "").strip()
SECRET_KEY = (os.getenv("BITHUMB_SECRET_KEY") or "").strip()

def inspect_ccxt_bithumb():
    # 2. 거래소 인스턴스 생성 및 verbose(상세 로그) 활성화
    exchange = ccxt.bithumb({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'verbose': True  # 실제 전송되는 HTTP 패킷 전체를 터미널에 출력
    })

    print("=== [1] CCXT 잔고 조회 요청 패킷 분석 ===")
    try:
        # 잔고 조회 실행 (실패 시 전송된 헤더와 URL이 터미널에 찍힘)
        balance = exchange.fetch_balance()
        print("[성공] 잔고 조회 결과:", balance)
    except Exception as e:
        print("\n[발생한 예외 요약]:", e)

if __name__ == "__main__":
    if not API_KEY or not SECRET_KEY:
        print("[오류] .env 파일에 키가 설정되지 않았습니다.")
    else:
        inspect_ccxt_bithumb()