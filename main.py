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
    
    market_str = "\n".join(market_list)

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
                msg = f"{icon} <b>{name}</b>: <b>{price:,}원</b> ({emoji} {change*100:.2f}%)"
                
                if m_id == 'KRW-SAND':
                    ret = ((price - MY_SAND_AVG) / MY_SAND_AVG) * 100
                    re_emoji = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f" (수익률: {re_emoji} <b>{ret:.2f}%</b>)"
                coin_messages.append(msg)
    except Exception as e:
        coin_messages.append(f"⚠️ 코인 오류: {e}")
    
    bitcoin_str = "\n".join(coin_messages)

    return market_str, bitcoin_str

def get_major_news():
    """Google 뉴스 RSS를 통해 주요 뉴스 10개를 가져옵니다."""
    news_list = []
    try:
        # Google 뉴스 RSS (대한민국/한국어)
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "xml") # XML 파서 사용
        
        items = soup.find_all("item")[:10] # 상위 10개 추출
        
        for i, item in enumerate(items, 1):
            title = item.title.text
            # 출처가 제목 끝에 보통 포함됨 (예: 뉴스제목 - 연합뉴스)
            link = item.link.text
            news_list.append(f"{i}. <a href='{link}'>{title}</a>")
            
    except Exception as e:
        news_list.append(f"⚠️ 뉴스 수집 오류: {e}")
    
    return "\n".join(news_list)

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
    exchange, coins = get_financial_info()
    news = get_major_news()
    
    final_parts = []
    
    # 1. 환율 및 코인 정보
    market_info = []
    if exchange: market_info.append(exchange)
    if coins: market_info.append(coins)
    
    if market_info:
        final_parts.append("💰 <b>[금융 시장 요약]</b>\n" + "\n".join(market_info))
    
    # 2. 주요 뉴스 정보
    if news:
        final_parts.append(f"📰 <b>[실시간 주요 뉴스 TOP 10]</b>\n\n{news}")
    
    if final_parts:
        # 가독성을 위해 섹션 사이를 구분선으로 나눕니다.
        send_telegram_message("\n\n" + "━" * 15 + "\n\n".join(final_parts))
