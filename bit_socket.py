from websocket import *
# 웹소켓 코드를 import 한다

# 비트코인 실시간 정보를 등록합니다.
        wm = WebSocketManager("ticker", ["BTC_KRW"])
        
        while True:
            try:
                data = wm.get()

                print(f"[{data['content']['date']}]/[{data['content']['time']}] 코인:{data['content']['symbol']}, 전일종가:{data['content']['prevClosePrice']}, 시가:{data['content']['openPrice']}, 고가:{data['content']['highPrice']}, 저가:{data['content']['lowPrice']}, 종가(현재가):{data['content']['closePrice']}")

            except:
                wm.terminate()   # 멀티 프로세스 종료