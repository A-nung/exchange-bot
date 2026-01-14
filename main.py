import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
import html 
from datetime import datetime, timedelta, timezone

# GitHub Secrets에서 환경변수 불러오기 
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 한국 시간(KST) 처리 로직 ---
    kst_tz = timezone(timedelta(hours=9))
    kst_now = datetime.now(kst_tz)
    current_hour = kst_now.hour
    is_news_time = (current_hour % 3 == 0)

    # ------------------------------------------------
    # 1. 환율 및 나스닥 선물 정보 (네이버 금융) 
    # ------------------------------------------------
    exchange_url = "https://finance.naver.com/marketindex/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(exchange_url, headers=headers, timeout=10)
        # 네이버 금융의 한글 깨짐 방지를 위한 인코딩 설정
        response.encoding = 'euc-kr' 
        soup = BeautifulSoup(response.text, "html.parser")
        
        market_list = []
        
        # 환율 정보 추출 
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            market_list.append(f"🇺🇸 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            market_list.append(f"🇯🇵 일본 JPY (100엔): <b>{jpy.text}원</b>")

        # 나스닥 100 선물 정보 추출 (금/은 대체)
        nasdaq = soup.select_one("a.head.nasdaq > div.head_info > span.value")
        if nasdaq:
            market_list.append(f"📉 나스닥 100 선물: <b>{nasdaq.text}</b>")
            
        market_str = "\n".join(market_list)
        
    except Exception as e:
        market_str = f"⚠️ 금융 정보 에러: {e}"

    # ------------------------------------------------
    # 2. 가상화폐 시세 (Upbit API - BTC, ETH, XRP, SAND) 
    # ------------------------------------------------
    upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND"
    
    try:
        response = requests.get(upbit_url, timeout=10)
        data_list = response.json()
        
        # 순서 보장을 위해 딕셔너리로 저장
        coin_data = {data['market']: data for data in data_list}
        coin_messages = []
        
        # 출력 대상 및 아이콘 설정
        targets = [
            ('KRW-BTC', '🟠', '비트코인 (BTC)'),
            ('KRW-ETH', '💠', '이더리움 (ETH)'),
            ('KRW-XRP', '🌊', '리플 (XRP)'),
            ('KRW-SAND', '🏖️', '샌드박스 (SAND)')
        ]
        
        for market_id, icon, name in targets:
            if market_id in coin_data:
                data = coin_data[market_id]
                trade_price = data['trade_price']
                change_rate = data['signed_change_rate']
                
                emoji = "🔺" if change_rate > 0 else "🔻" if change_rate < 0 else "-"
                price_fmt = f"{trade_price:,}"
                rate_fmt = f"{change_rate * 100:.2f}"
                
                base_msg = f"{icon} {name}: <b>{price_fmt}원</b> ({emoji} {rate_fmt}%)"
                
                # 샌드박스 수익률 계산 (평단가 898원 유지) 
                if market_id == 'KRW-SAND':
                    my_avg_price = 898 
                    my_return_rate = ((trade_price - my_avg_price) / my_avg_price) * 100
                    my_emoji = "🔥" if my_return_rate > 0 else "💧" if my_return_rate < 0 else "-"
                    my_return_fmt = f"{my_return_rate:.2f}"
                    profit_msg = f"   ↳ 내 수익률: {my_emoji} <b>{my_return_fmt}%</b> (평단 {my_avg_price}원)"
                    coin_messages.append(f"{base_msg}\n{profit_msg}")
                else:
                    coin_messages.append(base_msg)
        
        bitcoin_str = "\n\n".join(coin_messages)
        
    except Exception as e:
        bitcoin_str = f"⚠️ 코인 정보 에러: {e}"

    # ------------------------------------------------
    # 3. 구글 주요 뉴스 (RSS) 
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
            news_str = f"⚠️ 뉴스 정보 에러: {e}"

    return market_str, bitcoin_str, news_str

def send_telegram_message(message):
    # 텔레그램 메시지 전송 로직 
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
        message_parts.append(f"📊 <b>[시장 주요 지표]</b>\n{market_info}")
        message_parts.append(f"🚀 <b>[가상화폐 시세]</b>\n{coins}")
        if news:
             message_parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n{news}")
        
        final_message = "\n\n" + "—" * 15 + "\n\n" + "\n\n--------------------\n\n".join(message_parts)
        send_telegram_message(final_message)
