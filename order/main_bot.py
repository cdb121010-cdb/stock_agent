import os
import time
import datetime
import uuid
import hashlib
import urllib.parse
import jwt
import requests
import pandas as pd
from dotenv import load_dotenv

class Bithumb24hBot:
    def __init__(self, target_symbol: str = "XRP", is_paper_trading: bool = True):
        load_dotenv()
        self.access_key = (os.getenv("BITHUMB_API_KEY") or "").strip()
        self.secret_key = (os.getenv("BITHUMB_SECRET_KEY") or "").strip()
        self.telegram_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        self.telegram_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

        self.base_url = "https://api.bithumb.com/v1"
        self.target_symbol = target_symbol.upper()
        self.market = f"KRW-{self.target_symbol}"
        
        # 안전 스위치: True면 모의 매매(알림만), False면 실계좌 주문 집행
        self.is_paper_trading = is_paper_trading

        # 상태 관리 변수 (포지션 기억)
        self.has_position = False
        self.entry_price = 0.0
        self.buy_amount_krw = 6000.0  # 1회 매수 투입 원화 (최소 주문액 5,000원 이상)

        if not self.access_key or not self.secret_key:
            raise ValueError("[보안 오류] .env 파일의 빗썸 API 키를 확인해주세요.")

    # 텔레그램 알림 전송 (예외 격리)
    def send_alert(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"[텔레그램 통신 예외] {e}")

    # JWT 인증 헤더 생성기
    def _get_auth_headers(self, query_params: dict = None) -> dict:
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

    # 시세 및 캔들 조회
    def get_current_price(self) -> float:
        url = f"{self.base_url}/ticker?markets={self.market}"
        res = requests.get(url, timeout=5).json()
        return float(res[0]['trade_price'])

    def fetch_ohlcv(self, count: int = 30) -> pd.DataFrame:
        url = f"{self.base_url}/candles/minutes/1?market={self.market}&count={count}"
        res = requests.get(url, timeout=5).json()
        df = pd.DataFrame(res)
        df = df.iloc[::-1].reset_index(drop=True)
        df['trade_price'] = df['trade_price'].astype(float)
        return df

    def get_balance(self, currency: str = "KRW") -> float:
        url = f"{self.base_url}/accounts"
        res = requests.get(url, headers=self._get_auth_headers(), timeout=5).json()
        if isinstance(res, list):
            for item in res:
                if item.get("currency") == currency.upper():
                    return float(item.get("balance", 0.0))
        return 0.0

    # 이동평균선 전략 계산
    def analyze_market(self, df: pd.DataFrame) -> tuple[str, float, float]:
        df['MA5'] = df['trade_price'].rolling(window=5).mean()
        df['MA20'] = df['trade_price'].rolling(window=20).mean()

        prev_ma5, prev_ma20 = df['MA5'].iloc[-2], df['MA20'].iloc[-2]
        curr_ma5, curr_ma20 = df['MA5'].iloc[-1], df['MA20'].iloc[-1]

        if prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20:
            signal = "BUY"
        elif prev_ma5 >= prev_ma20 and curr_ma5 < curr_ma20:
            signal = "SELL"
        else:
            signal = "HOLD"

        return signal, curr_ma5, curr_ma20

    # 주문 집행
    def place_order(self, side: str, volume: float, price: float):
        params = {
            'market': self.market,
            'side': side,
            'volume': str(volume),
            'price': str(int(price)),
            'ord_type': 'limit'
        }
        headers = self._get_auth_headers(params)
        return requests.post(f"{self.base_url}/orders", json=params, headers=headers, timeout=5).json()

    # 1회 루프 로직
    def step(self):
        curr_price = self.get_current_price()
        df = self.fetch_ohlcv(count=30)
        signal, ma5, ma20 = self.analyze_market(df)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{now_str}] 현재가: {curr_price:,.0f}원 | MA5: {ma5:,.1f} | MA20: {ma20:,.1f} | 시그널: [{signal}] | 보유여부: {self.has_position}")

        # 1. 손절(Stop-Loss) 체크 (-2% 이상 하락 시 즉시 탈출)
        if self.has_position and self.entry_price > 0:
            yield_rate = (curr_price - self.entry_price) / self.entry_price * 100
            if yield_rate <= -2.0:
                msg = f"🚨 *[긴급 손절 발동]*\n• 종목: `{self.target_symbol}`\n• 손익률: `{yield_rate:.2f}%`\n• 강제 청산을 실행합니다."
                self.send_alert(msg)
                if not self.is_paper_trading:
                    coin_bal = self.get_balance(self.target_symbol)
                    self.place_order("ask", coin_bal, curr_price)
                self.has_position = False
                self.entry_price = 0.0
                return

        # 2. 매수 로직 (골든크로스 & 미보유 상태일 때만)
        if signal == "BUY" and not self.has_position:
            krw_balance = self.get_balance("KRW")
            msg = f"🚀 *[매수 진입 시그널]*\n• 종목: `{self.target_symbol}`\n• 매수가: `{curr_price:,.0f}원`\n• 가용 원화: `{krw_balance:,.0f}원`"
            
            if self.is_paper_trading:
                msg += "\n💡 _(모의 매매: 가상 진입 완료)_"
                self.has_position = True
                self.entry_price = curr_price
            else:
                if krw_balance >= self.buy_amount_krw:
                    vol = round(self.buy_amount_krw / curr_price, 4)
                    res = self.place_order("bid", vol, curr_price)
                    if "uuid" in res:
                        self.has_position = True
                        self.entry_price = curr_price
                        msg += f"\n• 주문 접수 완료: `{res['uuid']}`"
                    else:
                        msg += f"\n❌ 주문 거절: `{res}`"
            self.send_alert(msg)

        # 3. 매도 로직 (데드크로스 & 보유 상태일 때만)
        elif signal == "SELL" and self.has_position:
            profit_rate = (curr_price - self.entry_price) / self.entry_price * 100 if self.entry_price > 0 else 0.0
            msg = f"⚠️ *[청산 매도 시그널]*\n• 종목: `{self.target_symbol}`\n• 매도가: `{curr_price:,.0f}원`\n• 실현 손익률: `{profit_rate:+.2f}%`"
            
            if self.is_paper_trading:
                msg += "\n💡 _(모의 매매: 가상 청산 완료)_"
                self.has_position = False
                self.entry_price = 0.0
            else:
                coin_balance = self.get_balance(self.target_symbol)
                if coin_balance * curr_price >= 5000:
                    res = self.place_order("ask", coin_balance, curr_price)
                    if "uuid" in res:
                        self.has_position = False
                        self.entry_price = 0.0
                        msg += f"\n• 청산 접수 완료: `{res['uuid']}`"
            self.send_alert(msg)

    # 24시간 무한 루프 엔진 (정각 캔들 동기화)
    def start_24h_loop(self):
        mode_text = "모의(Paper Trading)" if self.is_paper_trading else "⚠️ 실전(Real Trading)"
        start_msg = f"🤖 *[빗썸 24시간 자동매매 가동]*\n• 대상: `{self.target_symbol}`\n• 모드: `{mode_text}`\n1분 단위 시장 감시를 시작합니다."
        print(start_msg)
        self.send_alert(start_msg)

        while True:
            try:
                # 1. 전략 1회 실행
                self.step()

                # 2. 다음 1분 01초 시점까지 정밀 대기 (정각 캔들 완성 동기화)
                now = datetime.datetime.now()
                remaining_seconds = 60 - now.second + 1
                time.sleep(remaining_seconds)

            except KeyboardInterrupt:
                print("\n[사용자 종료] 프로그램을 안전하게 정지합니다.")
                self.send_alert("🛑 *[알림]* 자동매매 봇이 수동으로 정지되었습니다.")
                break
            except Exception as e:
                err_msg = f"❌ *[런타임 예외 발생]*\n`{str(e)}`\n10초 후 재연결을 시도합니다."
                print(err_msg)
                self.send_alert(err_msg)
                time.sleep(10)


if __name__ == "__main__":
    # ⚠️ 안전 권장사항:
    # 1. 최초 며칠간은 is_paper_trading=True 상태로 텔레그램 시그널과 손익을 관찰하세요.
    # 2. 로직이 완전히 신뢰할 수 있을 때 is_paper_trading=False 로 변경하여 소액(6,000원) 실전에 투입합니다.
    bot = Bithumb24hBot(target_symbol="XRP", is_paper_trading=True)
    bot.start_24h_loop()