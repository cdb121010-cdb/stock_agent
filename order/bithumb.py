import os
import time
import uuid
import jwt
import requests
from dotenv import load_dotenv

# 1. 환경변수(.env) 로드 및 공백 제거
load_dotenv()
ACCESS_KEY = (os.getenv("BITHUMB_API_KEY") or "").strip()
SECRET_KEY = (os.getenv("BITHUMB_SECRET_KEY") or "").strip()

def get_bithumb_accounts():
    """빗썸 REST API (v1): 전체 보유 자산(계좌) 조회"""
    url = "https://api.bithumb.com/v1/accounts"
    
    # 2. 빗썸 v1 표준 페이로드 구성 (timestamp 필수 포함)
    payload = {
        'access_key': ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
        'timestamp': int(time.time() * 1000)  # 밀리초 단위 타임스탬프
    }
    
    # 3. HS256 알고리즘 기반 JWT 토큰 서명
    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    
    # PyJWT 버전에 따른 bytes -> str 변환 처리
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode('utf-8')
        
    headers = {
        'Authorization': f'Bearer {jwt_token}'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if not ACCESS_KEY or not SECRET_KEY:
        print("[경고] .env 파일에서 API Key를 읽어오지 못했습니다. 파일 위치와 변수명을 확인하세요.")
    else:
        result = get_bithumb_accounts()
        print("조회 결과:")
        print(result)