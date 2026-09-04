import os
import time
import uuid
import hashlib
import urllib.parse
import jwt
import requests
from dotenv import load_dotenv

# 1. 환경변수(.env) 로드
load_dotenv()
ACCESS_KEY = (os.getenv("BITHUMB_API_KEY") or "").strip()
SECRET_KEY = (os.getenv("BITHUMB_SECRET_KEY") or "").strip()

def _create_jwt_token(query_params: dict = None) -> str:
    """주문 요청 파라미터 위변조 방지용 JWT 서명 생성"""
    payload = {
        'access_key': ACCESS_KEY,
        'nonce': str(uuid.uuid4()),
        'timestamp': int(time.time() * 1000)
    }

    if query_params:
        query_string = urllib.parse.urlencode(query_params).encode("utf-8")
        m = hashlib.sha512()
        m.update(query_string)
        payload['query_hash'] = m.hexdigest()
        payload['query_hash_alg'] = 'SHA512'

    jwt_token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    if isinstance(jwt_token, bytes):
        jwt_token = jwt_token.decode('utf-8')
    return jwt_token

def get_current_price(market: str = "KRW-BTC") -> float:
    """빗썸 실시간 시세 조회"""
    url = f"https://api.bithumb.com/v1/ticker?markets={market}"
    res = requests.get(url, timeout=5).json()
    return float(res[0]['trade_price'])

def place_limit_order(market: str, side: str, volume: str, price: str):
    """지정가 주문 실행 (POST /v1/orders)"""
    url = "https://api.bithumb.com/v1/orders"
    params = {
        'market': market,
        'side': side,
        'volume': volume,
        'price': price,
        'ord_type': 'limit'
    }

    headers = {'Authorization': f'Bearer {_create_jwt_token(params)}'}
    
    try:
        response = requests.post(url, json=params, headers=headers, timeout=5)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def cancel_order(order_uuid: str):
    """주문 취소 실행 (DELETE /v1/order)"""
    url = "https://api.bithumb.com/v1/order"
    params = {'uuid': order_uuid}
    headers = {'Authorization': f'Bearer {_create_jwt_token(params)}'}
    
    try:
        response = requests.delete(url, params=params, headers=headers, timeout=5)
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if not ACCESS_KEY or not SECRET_KEY:
        print("[경고] API 키가 올바르게 설정되지 않았습니다.")
        exit()

    market_symbol = "KRW-BTC"
    
    # 1. 실시간 시세 확인 (새로운 로직의 첫 줄)
    current_price = get_current_price(market_symbol)
    print(f"1. [{market_symbol}] 현재 시장 가격: {current_price:,.0f} 원")

    # 2. 안전 주문 가격 계산: 현재가의 50% 수준 (약 5,300만 원 선)
    # 거래소 하한선(10%)을 확실하게 넘기며, 시장가와 수천만 원 차이가 나므로 즉시 체결 위험 제로
    safe_price = int((current_price * 0.5) // 1000 * 1000)  # 1,000원 단위 호가 정렬

    # 3. 최소 주문 금액(5,000원)을 충족하는 6,000원 기준 수량 역산
    target_budget = 6000.0
    calculated_volume = round(target_budget / safe_price, 8)
    actual_order_total = safe_price * calculated_volume

    print(f"2. [산출된 안전 주문 파라미터]")
    print(f"   - 안전 주문 단가: {safe_price:,.0f} 원")
    print(f"   - 안전 주문 수량: {calculated_volume:.8f} BTC")
    print(f"   - 예상 총 결제액: {actual_order_total:,.0f} 원")

    # 4. 주문 전송
    print(f"\n3. [{market_symbol}] 매수 주문 전송 시도...")
    order_result = place_limit_order(
        market=market_symbol,
        side="bid",
        volume=f"{calculated_volume:.8f}",
        price=str(safe_price)
    )
    print("주문 응답 결과:", order_result)

    # 5. 발급된 UUID로 3초 후 즉시 취소
    if isinstance(order_result, dict) and "uuid" in order_result:
        created_uuid = order_result["uuid"]
        print(f"\n4. 주문 접수 성공 (UUID: {created_uuid})")
        print("   -> 3초 후 주문 취소를 진행합니다...")
        time.sleep(3)
        cancel_result = cancel_order(created_uuid)
        print("취소 응답 결과:", cancel_result)
    else:
        print("\n[알림] 주문이 생성되지 않았습니다.")