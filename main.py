import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
import html 
from datetime import datetime, timedelta

# GitHub 금고에서 환경변수 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 한국 시간(KST) 및 3시간 뉴스 체크 로직 ---
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    current_hour = kst_now.hour
    is_news_time = (current_hour % 3 == 0)

    # ------------------------------------------------
    # 1. 환율 정보 (네이버 금융)
    # ------------------------------------------------
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

    # ------------------------------------------------
    # 2. 가상화폐 시세 (비트코인 + 샌드박스)
    # ------------------------------------------------
    # BTC와 SAND 두 개의 시세를 한번에 요청합니다.
    upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-SAND"
    
    try:
        response = requests.get(upbit_url, timeout=10)
        data_list = response.json() # 리스트 형태로 반환됨
        
        coin_messages = []
        
        for data in data_list:
            market = data['market']
            trade_price = data['trade_price']
            change_rate = data['signed_change_rate']
            
            # 등락 이모지 결정
            if change_rate > 0:
                emoji = "🔺"
            elif change_rate < 0:
                emoji = "🔻"
            else:
                emoji = "-"
            
            price_fmt = f"{trade_price:,}"
            rate_fmt = f"{change_rate * 100:.2f}"
            
            # --- A. 비트코인일 경우 ---
            if market == 'KRW-BTC':
                coin_messages.append(f"비트코인 (BTC): <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)")
            
            # --- B. 샌드박스일 경우 (평단가 로직 추가) ---
            elif market == 'KRW-SAND':
                # 기본 시세 정보
                base_msg = f"샌드박스 (SAND): <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)"
                
                # [내 평단가 계산 로직]
                my_avg_price = 898  # 설정하신 평단가
                my_return_rate = ((trade_price - my_avg_price) / my_avg_price) * 100
                
                # 수익률 이모지
                if my_return_rate > 0:
                    my_emoji = "🔥" # 수익 중일 때
                elif my_return_rate < 0:
                    my_emoji = "💧" # 손실 중일 때
                else:
                    my_emoji = "-"
                
                my_return_fmt = f"{my_return_rate:.2f}"
                
                # 들여쓰기로 내 수익률 표시 추가
                profit_msg = f"   ↳ 내 수익률: {my_emoji} <b>{my_return_fmt}%</b> (평단 {my_avg_price}원)"
                
                coin_messages.append(f"{base_msg}\n{profit_msg}")
        
        bitcoin_str = "\n\n".join(coin_messages)
        
    except Exception as e:
        bitcoin_str = f"코인 정보 에러: {e}"

    # ------------------------------------------------
    # 3. 구글 주요 뉴스 (3시간 간격)
    # ------------------------------------------------
    news_str = ""
    
    if is_news_time:
        google_news_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        
        try:
            response = requests.get(google_news_url, timeout=10)
            root = ET.fromstring(response.content)
            
            news_list = []
            items = root.findall('./channel/item')
            
            for item in items[:10]:
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
    rates, coins, news = get_financial_info()
    
    if rates or coins:
        print("데이터 가져오기 성공")
        
        message_parts = []
        
        # 1. 환율
        message_parts.append(f"💰 <b>[현재 환율 정보]</b>\n{rates}")
        
        # 2. 코인 (비트코인 + 샌드박스)
        message_parts.append(f"🚀 <b>[가상화폐 시세 (Upbit)]</b>\n{coins}")
        
        # 3. 뉴스 (해당 시간에만)
        if news:
             message_parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n{news}")
        
        final_message = "\n\n--------------------\n\n".join(message_parts)
        
        send_telegram_message(final_message)
    else:
        print("데이터를 가져오지 못했습니다.")
