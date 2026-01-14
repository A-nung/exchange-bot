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
    # --- 한국 시간(KST) 및 뉴스 시간 체크 --- 
    kst_tz = timezone(timedelta(hours=9))
    kst_now = datetime.now(kst_tz)
    current_hour = kst_now.hour
    is_news_time = (current_hour % 3 == 0)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # ------------------------------------------------
    # 1. 환율 정보 (나스닥 제거) 
    # ------------------------------------------------
    market_list = []
    try:
        exchange_url = "https://finance.naver.com/marketindex/"
        response = requests.get(exchange_url, headers=headers, timeout=10)
        response.encoding = 'euc-kr' 
        soup = BeautifulSoup(response.text, "html.parser")
        
        usd = soup.select_one("a.head.usd span.value")
        if usd: market_list.append(f"💵 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy span.value")
        if jpy: market_list.append(f"💴 일본 JPY (100엔): <b>{jpy.text}원</b>")
    except Exception:
        market_list.append(f"⚠️ 환율 정보 수집 에러")

    market_str = "\n".join(market_list)

    # ------------------------------------------------
    # 2. 가상화폐 시세 (가독성 강화 버전) 
    # ------------------------------------------------
    upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND"
    try:
        response = requests.get(upbit_url, timeout=10)
        data_list = response.json()
        coin_data = {data['market']: data for data in data_list}
        coin_messages = []
        
        targets = [
            ('KRW-BTC', '🟠', '비트코인 (BTC)'),
            ('KRW-ETH', '💠', '이더리움 (ETH)'),
            ('KRW-XRP', '🌊', '리플 (XRP)'),
            ('KRW-SAND', '🏖️', '샌드박스 (SAND)')
        ]
        
        for m_id, icon, name in targets:
            if m_id in coin_data:
                d = coin_data[m_id]
                p = d['trade_price']
                c = d['signed_change_rate']
                emoji = "🔺" if c > 0 else "🔻" if c < 0 else "-"
                
                # 가독성을 위해 코인 이름과 가격을 강조
                msg = f"{icon} <b>{name}</b>\n현재가: <b>{p:,}원</b> ({emoji} {c*100:.2f}%)"
                
                if m_id == 'KRW-SAND':
                    avg = 898 # 평단가 고정 
                    ret = ((p - avg) / avg) * 100
                    e = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f"\n      ↳ 수익률: {e} <b>{ret:.2f}%</b>"
                
                coin_messages.append(msg)
        
        # 코인별로 두 줄 바꿈 처리하여 구분감 확보
        bitcoin_str = "\n\n".join(coin_messages)
    except Exception:
        bitcoin_str = f"⚠️ 코인 정보 에러"

    # ------------------------------------------------
    # 3. 구글 뉴스 (RSS - 가독성 강화 버전) 
    # ------------------------------------------------
    news_str = ""
    if is_news_time:
        try:
            res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=10)
            root = ET.fromstring(res.content)
            items = root.findall('./channel/item')[:10]
            
            news_list = []
            for idx, i in enumerate(items, 1):
                title = html.escape(i.find('title').text)
                link = i.find('link').text
                # 번호를 붙이고 뉴스 사이에 여백을 주어 구분
                news_list.append(f"{idx}. <a href='{link}'>{title}</a>")
            
            # 뉴스 항목 간 두 줄 바꿈 적용
            news_str = "\n\n".join(news_list)
        except:
            news_str = "⚠️ 뉴스 로딩 실패"

    return market_str, bitcoin_str, news_str

def send_telegram_message(message):
    # 텔레그램 메시지 전송 
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML', 
        'disable_web_page_preview': True
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    market_info, coins, news = get_financial_info()
    
    if market_info or coins:
        message_parts = []
        
        # 섹션별 명확한 제목과 두 줄 바꿈 간격 적용
        if market_info:
            message_parts.append(f"📊 <b>[주요 환율 정보]</b>\n{market_info}")
        
        if coins:
            message_parts.append(f"🚀 <b>[가상화폐 시세]</b>\n\n{coins}")
        
        if news:
            message_parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n\n{news}")
        
        # 섹션 사이 간격은 세 줄 바꿈으로 매우 명확하게 구분
        final_message = "\n\n\n".join(message_parts)
        send_telegram_message(final_message)
