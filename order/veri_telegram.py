import os
import requests
from dotenv import load_dotenv

# 1. .env 로드 및 값 형태 점검
load_dotenv()
token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

print("=== [1] .env 설정값 자가 진단 ===")
print(f"• BOT_TOKEN 앞 10자리: {token[:10]}... (총 길이: {len(token)})")
print(f"• 현재 설정된 CHAT_ID : '{chat_id}'")

if not chat_id.lstrip('-').isdigit():
    print("⚠️ [경고] CHAT_ID에 문자가 포함되어 있습니다! 순수 숫자(예: 123456789)여야 합니다.")

# 2. 텔레그램 서버 수신함(getUpdates) 조회
print("\n=== [2] 텔레그램 서버 수신함 확인 ===")
url = f"https://api.telegram.org/bot{token}/getUpdates"

try:
    res = requests.get(url, timeout=5).json()
    if not res.get("ok"):
        print(f"❌ 토큰 오류 발생: {res.get('description')}")
    else:
        updates = res.get("result", [])
        if not updates:
            print("❌ 수신함이 비어 있습니다!")
            print("👉 [해결 행동]: 스마트폰 텔레그램 앱에서 내 봇을 검색해 들어간 뒤,")
            print("             '시작'(/start) 버튼을 누르고 '안녕'이라고 메시지를 1개 보내세요.")
        else:
            latest_chat = updates[-1].get("message", {}).get("chat", {})
            real_id = latest_chat.get("id")
            user_name = latest_chat.get("first_name", "사용자")
            
            print(f"✅ 텔레그램 서버에서 확인된 실제 정보:")
            print(f"   - 사용자 이름: {user_name}")
            print(f"   - 실제 숫자 CHAT_ID: {real_id}")
            
            if str(real_id) == str(chat_id):
                print("\n🎉 .env의 CHAT_ID와 서버 ID가 정확히 일치합니다!")
            else:
                print(f"\n⚠️ .env 파일의 TELEGRAM_CHAT_ID={real_id} 로 변경해야 합니다.")

except Exception as e:
    print(f"❌ 네트워크 예외: {e}")