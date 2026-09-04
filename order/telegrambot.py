import os
import argparse
import requests
from dotenv import load_dotenv

# 1. .env 파일에서 토큰과 Chat ID 로드
load_dotenv()
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_ID = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

def send_message(message: str) -> bool:
    """텔레그램 대화방으로 메시지를 전송하는 함수"""
    if not BOT_TOKEN or not CHAT_ID:
        print("[경고] .env 파일에 TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 없습니다.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ [전송 성공] {message}")
            return True
        else:
            print(f"❌ [전송 실패] 상태 코드: {response.status_code}, 내용: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ [네트워크 오류] {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="내 휴대폰으로 텔레그램 메시지 보내기")
    
    # nargs="*"로 지정하여 인자가 0개여도 에러 없이 통과시킵니다.
    parser.add_argument("messages", nargs="*", help="보낼 메시지들")
    args = parser.parse_args()

    # 인자를 입력하지 않고 실행한 경우 -> 기본 안내 문구 발송
    if not args.messages:
        print("[알림] 입력된 인자가 없어 기본 테스트 문구를 발송합니다.")
        send_message("🤖 [자동매매 봇] 텔레그램 연동이 정상적으로 완료되었습니다!")
    else:
        # 인자를 입력하고 실행한 경우 -> 입력한 내용 발송
        for msg in args.messages:
            send_message(msg)

if __name__ == "__main__":
    main()