import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
import html 
# timezone 모듈을 추가로 임포트합니다.
from datetime import datetime, timedelta, timezone

# GitHub Secrets에서 환경변수 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- [수정] 한국 시간(KST) 처리 로직 ---
    # utcnow() 대신 timezone을 명시적으로 설정하여 KST를 계산합니다.
    kst_tz = timezone(timedelta(hours=9))
    kst_now = datetime.now(kst_tz)
    current_hour = kst_now.hour
    is_news_time = (current_hour % 3 == 0)

    # ------------------------------------------------
    # 1. 환율 및 금/은 정보 (네이버 금융)
    # ------------------------------------------------
    exchange_url = "https://finance.naver.com/marketindex/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(exchange_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        
        market_list = []
        
        # 환율 정보
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            market_list.append(f"🇺🇸 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            market_list.append(f"🇯🇵 일본 JPY (100엔): <b>{jpy.text}원</b>")

        # --- [추가] 금/은 시세 정보 ---
        # 국제 금 시세
        gold_intl = soup.select_one("a.head.gold_intl > div.head_info > span.value")
        if gold_intl:
            market_list.append(f"🏆 국제 금: <b>{gold_intl.text}달러/온스</b>")

        # 국내 금 시세
        gold_dom = soup.select_one("a.head.gold_domestic > div.head_info > span.value")
        if gold_dom:
            market_list.append(f"🥇 국내 금: <b>{gold_dom.text}원/g</b>")

        # 은 시세
        silver = soup.select_one("a.head.silver > div.head_info > span.value")
        if silver:
            market_list.append(f"🥈 국제 은: <b>{silver.text}달러/온스</b>")
            
        market_str = "\n".join(market_list)
        
    except Exception as e:
        market_str = f"금융 정보 에러: {e}"

    # ------------------------------------------------
    # 2. 가상화폐 시세 (비트코인 + 샌드박스)
    # ------------------------------------------------
    upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-SAND"
    
    try:
        response = requests.get(upbit_url, timeout=10)
        data_list = response.json()
        coin_messages = []
        
        for data in data_list:
            market = data['market']
            trade_price = data['trade_price']
            change_rate = data['signed_change_rate']
            
            emoji = "🔺" if change_rate > 0 else "🔻" if change_rate < 0 else "-"
            price_fmt = f"{trade_price:,}"
            rate_fmt = f"{change_rate * 100:.2f}"
            
            if market == 'KRW-BTC':
                coin_messages.append(f"비트코인 (BTC): <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)")
            elif market == 'KRW-SAND':
                base_msg = f"샌드박스 (SAND): <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)"
                my_avg_price = 898 
                my_return_rate = ((trade_price - my_avg_price) / my_avg_price) * 100
                my_emoji = "🔥" if my_return_rate > 0 else "💧" if my_return_rate < 0 else "-"
                my_return_fmt = f"{my_return_rate:.2f}"
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

    return market_str, bitcoin_str, news_str

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
    market_info, coins, news = get_financial_info()
    
    if market_info or coins:
        message_parts = []
        # 제목을 [금융 및 시장 지표]로 변경
        message_parts.append(f"💰 <b>[금융 및 시장 지표]</b>\n{market_info}")
        message_parts.append(f"🚀 <b>[가상화폐 시세 (Upbit)]</b>\n{coins}")
        if news:
             message_parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n{news}")
        
        final_message = "\n\n--------------------\n\n".join(message_parts)
        send_telegram_message(final_message)
