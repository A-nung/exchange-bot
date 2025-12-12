import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
import html 
from datetime import datetime, timedelta # 시간 계산을 위해 추가

# GitHub 금고에서 환경변수 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 한국 시간(KST) 계산 ---
    # 서버 시간(UTC) + 9시간 = 한국 시간
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    current_hour = kst_now.hour
    
    # 3시간 간격 체크 (0, 3, 6, 9, 12 ... 시에만 True)
    is_news_time = (current_hour % 3 == 0)

    # --- 1. 환율 정보 (항상 실행) ---
    exchange_url = "https://finance.naver.com/marketindex/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(exchange_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        
        exchange_list = []
        
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            exchange_list.append(f"🇺🇸 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            exchange_list.append(f"🇯🇵 일본 JPY (100엔): <b>{jpy.text}원</b>")
            
        exchange_str = "\n".join(exchange_list)
        
    except Exception as e:
        exchange_str = f"환율 정보 에러: {e}"

    # --- 2. 비트코인 시세 (항상 실행) ---
    upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC"
    
    try:
        response = requests.get(upbit_url, timeout=10)
        data = response.json()[0]
        
        trade_price = data['trade_price']
        change_rate = data['signed_change_rate']
        
        if change_rate > 0:
            emoji = "🔺"
        elif change_rate < 0:
            emoji = "🔻"
        else:
            emoji = "-"
            
        price_fmt = f"{trade_price:,}"
        rate_fmt = f"{change_rate * 100:.2f}"
        
        bitcoin_str = f"🪙 비트코인 (BTC): <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)"
        
    except Exception as e:
        bitcoin_str = f"비트코인 정보 에러: {e}"

    # --- 3. 구글 주요 뉴스 (3시간마다 실행) ---
    news_str = "" # 기본값은 빈 문자열
    
    if is_news_time:
        google_news_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        
        try:
            response = requests.get(google_news_url, timeout=10)
            root = ET.fromstring(response.content)
            
            news_list = []
            items = root.findall('./channel/item')
            
            for item in items[:20]:
                title = html.escape(item.find('title').text)
                link = item.find('link').text
                news_list.append(f"📰 <a href='{link}'>{title}</a>")
                
            news_str = "\n\n".join(news_list)
            
        except Exception as e:
            news_str = f"뉴스 정보 에러: {e}"

    return exchange_str, bitcoin_str, news_str

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    data = {
        'chat_id': CHAT_ID, 
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True 
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    rates, btc, news = get_financial_info()
    
    if rates or btc:
        print("데이터 가져오기 성공")
        
        # 메시지 조각 모음 (리스트 활용하여 동적 생성)
        message_parts = []
        
        # 1. 환율
        message_parts.append(f"💰 <b>[현재 환율 정보]</b>\n{rates}")
        
        # 2. 비트코인
        message_parts.append(f"🚀 <b>[가상화폐 시세 (Upbit)]</b>\n{btc}")
        
        # 3. 뉴스 (데이터가 있을 때만 추가)
        if news:
             message_parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n{news}")
        
        # 각 섹션을 구분선으로 연결
        final_message = "\n\n--------------------\n\n".join(message_parts)
        
        send_telegram_message(final_message)
    else:
        print("데이터를 가져오지 못했습니다.")
