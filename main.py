import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta, timezone

# ------------------------------------------------
# 1. 환경 설정 및 상수 정의 
# ------------------------------------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') [cite: 1]
CHAT_ID = os.environ.get('CHAT_ID') [cite: 1]              
MY_SAND_AVG = 898 [cite: 1]                                 

# HTTP 요청 시 사용할 헤더
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
} [cite: 1]

def get_financial_info():
    """금융 지표 및 코인 시세를 수집하여 반환합니다."""
    
    # ------------------------------------------------
    # 2. 주요 환율 정보 수집 (네이버 금융) 
    # ------------------------------------------------
    market_list = []
    try:
        url = "https://finance.naver.com/marketindex/" [cite: 1]
        res = requests.get(url, headers=HEADERS, timeout=10) [cite: 1]
        res.encoding = 'euc-kr' [cite: 1]
        soup = BeautifulSoup(res.text, "html.parser") [cite: 1]
        
        usd = soup.select_one("a.head.usd span.value") [cite: 1]
        if usd: market_list.append(f"💵 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy span.value") [cite: 1]
        if jpy: market_list.append(f"💴 일본 JPY (100엔): <b>{jpy.text}원</b>")
    except Exception:
        market_list.append("⚠️ 환율 정보를 가져오지 못했습니다.")
    
    market_str = "\n\n".join(market_list)

    # ------------------------------------------------
    # 3. 가상화폐 시세 수집 (Upbit API) 
    # ------------------------------------------------
    coin_messages = []
    try:
        upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND" [cite: 1]
        res = requests.get(upbit_url, timeout=10).json() [cite: 1]
        coin_data = {item['market']: item for item in res} [cite: 1]
        
        targets = [
            ('KRW-BTC', '🟠', '비트코인 (BTC)'),
            ('KRW-ETH', '💠', '이더리움 (ETH)'),
            ('KRW-XRP', '🌊', '리플 (XRP)'),
            ('KRW-SAND', '🏖️', '샌드박스 (SAND)')
        ]
        
        for m_id, icon, name in targets:
            if m_id in coin_data:
                d = coin_data[m_id]
                price = d['trade_price'] [cite: 1]
                change = d['signed_change_rate'] [cite: 1]
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "-"
                
                msg = f"{icon} <b>{name}</b>\n현재가: <b>{price:,}원</b> ({emoji} {change*100:.2f}%)"
                
                if m_id == 'KRW-SAND':
                    ret = ((price - MY_SAND_AVG) / MY_SAND_AVG) * 100 [cite: 1]
                    re_emoji = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f"\n      ↳ 수익률: {re_emoji} <b>{ret:.2f}%</b>"
                
                coin_messages.append(msg)
    except Exception:
        coin_messages.append("⚠️ 코인 시세를 가져오지 못했습니다.")
    bitcoin_str = "\n\n".join(coin_messages)

    return market_str, bitcoin_str

def send_telegram_message(message):
    """최종 구성된 메시지를 텔레그램으로 전송합니다. """
    if not TELEGRAM_TOKEN or not CHAT_ID: return [cite: 1]
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage" [cite: 1]
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML', 
        'disable_web_page_preview': True [cite: 1]
    }
    requests.post(url, data=payload) [cite: 1]

if __name__ == "__main__":
    exchange, coins = get_financial_info()
    
    final_parts = []
    if exchange:
        final_parts.append(f"📊 <b>[주요 환율 정보]</b>\n\n{exchange}")
    if coins:
        final_parts.append(f"🚀 <b>[가상화폐 시세]</b>\n\n{coins}")
    
    if final_parts:
        send_telegram_message("\n\n\n".join(final_parts))
