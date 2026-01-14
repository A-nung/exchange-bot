import requests
from bs4 import BeautifulSoup
import os

# ------------------------------------------------
# 1. 환경 설정 및 상수 정의 
# ------------------------------------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') 
CHAT_ID = os.environ.get('CHAT_ID')               
MY_SAND_AVG = 898                                 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_financial_info():
    """환율 및 코인 시세를 수집합니다."""
    
    # --- 1. 환율 수집 ---
    market_list = []
    try:
        url = "https://finance.naver.com/marketindex/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, "html.parser")
        
        usd = soup.select_one("a.head.usd span.value")
        if usd: market_list.append(f"💵 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy span.value")
        if jpy: market_list.append(f"💴 일본 JPY (100엔): <b>{jpy.text}원</b>")
    except Exception as e:
        market_list.append(f"⚠️ 환율 오류: {e}")
    
    market_str = "\n\n".join(market_list)

    # --- 2. 코인 시세 수집 ---
    coin_messages = []
    try:
        upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND"
        res = requests.get(upbit_url, timeout=10).json()
        coin_data = {item['market']: item for item in res}
        
        targets = [
            ('KRW-BTC', '🟠', '비트코인'),
            ('KRW-ETH', '💠', '이더리움'),
            ('KRW-XRP', '🌊', '리플'),
            ('KRW-SAND', '🏖️', '샌드박스')
        ]
        
        for m_id, icon, name in targets:
            if m_id in coin_data:
                d = coin_data[m_id]
                price = d['trade_price']
                change = d['signed_change_rate']
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "-"
                msg = f"{icon} <b>{name}</b>\n현재가: <b>{price:,}원</b> ({emoji} {change*100:.2f}%)"
                
                if m_id == 'KRW-SAND':
                    ret = ((price - MY_SAND_AVG) / MY_SAND_AVG) * 100
                    re_emoji = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f"\n      ↳ 수익률: {re_emoji} <b>{ret:.2f}%</b>"
                coin_messages.append(msg)
    except Exception as e:
        coin_messages.append(f"⚠️ 코인 오류: {e}")
    
    bitcoin_str = "\n\n".join(coin_messages)

    return market_str, bitcoin_str

def send_telegram_message(message):
    """메시지 전송"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 CHAT_ID가 설정되지 않았습니다.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    res = requests.post(url, data=payload)
    if res.status_code != 200:
        print(f"텔레그램 전송 실패: {res.text}")

if __name__ == "__main__":
    # 여기서 정확히 2개만 받는지 확인하세요!
    exchange, coins = get_financial_info()
    
    final_parts = []
    if exchange:
        final_parts.append(f"📊 <b>[주요 환율 정보]</b>\n\n{exchange}")
    if coins:
        final_parts.append(f"🚀 <b>[가상화폐 시세]</b>\n\n{coins}")
    
    if final_parts:
        send_telegram_message("\n\n\n".join(final_parts))
