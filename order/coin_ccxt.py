import os
import time
import uuid
import hashlib
import urllib.parse
import jwt
import requests
import pandas as pd
from dotenv import load_dotenv

class BithumbTradingBot:
    """빗썸 최신 v1 규격 기반 전략 자동매매 봇"""

    def __init__(self, target_symbol: str = "XRP"):
        load_dotenv()
        self.access_key = (os.getenv("BITHUMB_API_KEY") or "").strip()
        self.secret_key = (os.getenv("BITHUMB_SECRET_KEY") or "").strip()
        self.base_url = "https://api.bithumb.com/v1"
        self.target_symbol = target_symbol.upper()
        self.market = f"KRW-{self.target_symbol}"

        if not self.access_key or not self.secret_key:
            raise ValueError("[보안 오류] .env 파일에 API 키가 설정되지 않았습니다.")

    # -------------------------------------------------------------
    # [1] 인증 및 보안 모듈 (JWT / SHA-512)
    # -------------------------------------------------------------
    def _get_auth_headers(self, query_params: dict = None) -> dict:
        """파라미터 변조 방지용 해시가 포함된 JWT 인증 헤더 생성"""
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
            'timestamp': int(time.time() * 1000)
        }
        if query_params:
            query_string = urllib.parse.urlencode(query_params).encode("utf-8")
            m = hashlib.sha512()
            m.update(query_string)
            payload['query_hash'] = m.hexdigest()
            payload['query_hash_alg'] = 'SHA512'

        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        return {'Authorization': f'Bearer {token}'}

    # -------------------------------------------------------------
    # [2] 데이터 수집 계층 (Public API)
    # -------------------------------------------------------------
    def get_current_price(self) -> float:
        """실시간 현재가 조회"""
        url = f"{self.base_url}/ticker?markets={self.market}"
        res = requests.get(url, timeout=5).json()
        return float(res[0]['trade_price'])

    def fetch_ohlcv(self, count: int = 30) -> pd.DataFrame:
        """
        최근 분봉(1분봉 기준) 캔들 차트 데이터를 수집하여 Pandas DataFrame으로 가공
        """
        url = f"{self.base_url}/candles/minutes/1?market={self.market}&count={count}"
        res = requests.get(url, timeout=5).json()
        
        # 최신순 정렬 데이터를 시간순(오름차순)으로 변환
        df = pd.DataFrame(res)
        df = df.iloc[::-1].reset_index(drop=True)
        
        # 수치형 데이터 변환
        df['trade_price'] = df['trade_price'].astype(float) # 종가
        df['opening_price'] = df['opening_price'].astype(float) # 시가
        df['high_price'] = df['high_price'].astype(float) # 고가
        df['low_price'] = df['low_price'].astype(float) # 저가
        return df

    # -------------------------------------------------------------
    # [3] 잔고 조회 및 리스크 관리 계층
    # -------------------------------------------------------------
    def get_balance(self, currency: str = "KRW") -> float:
        """특정 자산의 가용 잔고(free) 조회"""
        url = f"{self.base_url}/accounts"
        headers = self._get_auth_headers()
        res = requests.get(url, headers=headers, timeout=5).json()
        
        if isinstance(res, list):
            for item in res:
                if item.get("currency") == currency.upper():
                    return float(item.get("balance", 0.0))
        return 0.0

    # -------------------------------------------------------------
    # [4] 전략 분석 계층 (단기/장기 이동평균선 크로스 전략 예시)
    # -------------------------------------------------------------
    def analyze_strategy(self, df: pd.DataFrame) -> str:
        """
        단기 이평선(5)과 장기 이평선(20)을 계산하여 매매 시그널 도출
        :return: 'BUY'(골든크로스), 'SELL'(데드크로스), 'HOLD'(유지)
        """
        df['MA5'] = df['trade_price'].rolling(window=5).mean()
        df['MA20'] = df['trade_price'].rolling(window=20).mean()

        # 최근 2개 봉의 추세 비교
        prev_ma5 = df['MA5'].iloc[-2]
        prev_ma20 = df['MA20'].iloc[-2]
        curr_ma5 = df['MA5'].iloc[-1]
        curr_ma20 = df['MA20'].iloc[-1]

        # 골든크로스 (단기선이 장기선을 상향 돌파)
        if prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20:
            return "BUY"
        # 데드크로스 (단기선이 장기선을 하향 돌파)
        elif prev_ma5 >= prev_ma20 and curr_ma5 < curr_ma20:
            return "SELL"
        return "HOLD"

    # -------------------------------------------------------------
    # [5] 주문 집행 계층 (Execution)
    # -------------------------------------------------------------
    def execute_order(self, side: str, volume: float, price: float):
        """지정가 매수/매도 주문 전송"""
        params = {
            'market': self.market,
            'side': side,
            'volume': str(volume),
            'price': str(int(price)),
            'ord_type': 'limit'
        }
        headers = self._get_auth_headers(params)
        return requests.post(f"{self.base_url}/orders", json=params, headers=headers, timeout=5).json()

    # -------------------------------------------------------------
    # [6] 메인 실행 루프 (모의 실행/로그 모드)
    # -------------------------------------------------------------
    def run_simulation_cycle(self):
        """1회 분석 및 모의 판단 사이클"""
        print(f"\n================ [{self.target_symbol}] 전략 분석 사이클 시작 ================")
        
        # 1. 캔들 데이터 수집
        df = self.fetch_ohlcv(count=30)
        current_price = self.get_current_price()
        print(f"1. 실시간 현재가: {current_price:,.1f} 원")

        # 2. 전략 시그널 판별
        signal = self.analyze_strategy(df)
        ma5_val = df['MA5'].iloc[-1]
        ma20_val = df['MA20'].iloc[-1]
        print(f"2. 지표 현황: 5분 MA ({ma5_val:,.1f}원) vs 20분 MA ({ma20_val:,.1f}원)")
        print(f"3. 전략 분석 결과 시그널: [{signal}]")

        # 3. 리스크 관리 및 주문 시뮬레이션
        krw_balance = self.get_balance("KRW")
        coin_balance = self.get_balance(self.target_symbol)
        print(f"4. 계좌 상태: 원화 {krw_balance:,.1f}원 | {self.target_symbol} {coin_balance:.4f}개")

        if signal == "BUY":
            print("   -> [매수 시그널 포착] 계좌 잔고 확인 후 주문 집행 조건을 검토합니다.")
        elif signal == "SELL":
            print("   -> [매도 시그널 포착] 보유 수량 확인 후 청산 조건을 검토합니다.")
        else:
            print("   -> [관망] 진입/청산 조건이 만족되지 않아 포지션을 유지합니다.")


if __name__ == "__main__":
    # 리플(XRP)을 대상으로 모의 분석 루프 실행
    bot = BithumbTradingBot(target_symbol="XRP")
    bot.run_simulation_cycle()