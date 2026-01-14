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
    kst_tz = timezone(timedelta(hours=9))
    kst_now = datetime.now(kst_tz)
    current_hour = kst_now.hour
    is_news_time = (current_hour % 3 == 0)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    market_list = []

    # 1-1. 환율 정보 (네이버 금융 메인)
    try:
        exchange_url = "https://finance.naver.com/marketindex/"
        response = requests.get(exchange_url, headers=headers, timeout=10)
        response.encoding = 'euc-kr'
        soup = BeautifulSoup(response.text, "html.parser")
        
        usd = soup.select_one("a.head.usd span.value")
        if usd: market_list.append(f"🇺🇸 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy span.value")
        if jpy: market_list.append(f"🇯🇵 일본 JPY (100엔): <b>{jpy.text}원</b>")
    except Exception as e:
        market_list.append(f"⚠️ 환율 에러: {e}")

    # 1-2. 나스닥 100 선물 (전용 상세 페이지에서 직접 수집)
    try:
        # 탭 구조 문제를 피하기 위해 나스닥 선물 상세 페이지를 직접 호출합니다.
        nasdaq_url = "https://finance.naver.com/marketindex/worldExchangeDetail.naver?marketindexCode=NAS@NX"
        nas_res = requests.get(nasdaq_url, headers=headers, timeout=10)
        nas_res.encoding = 'euc-kr'
        nas_soup = BeautifulSoup(nas_res.text, "html.parser")
        
        # 상세 페이지의 지수 값 추출
        nasdaq_val = nas_soup.select_one("div.graph_info span.value")
        if nasdaq_val:
            market_list.append(f"📉 나스닥 100 선물: <b>{nasdaq_val.text}</b>")
        else:
            market_list.append(f"📉 나스닥 100 선물: <b>수집 실패</b>")
    except Exception:
        market_list.append(f"📉 나스닥 100 선물: <b>에러</b>")

    market_str = "\n".join(market_list)

    # 2. 가상화폐 시세 (Upbit API)
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
                
                msg = f"{icon} {name}: <b>{p:,}원</b> ({emoji} {c*100:.2f}%)"
                if m_id == 'KRW-SAND':
                    avg = 898 # 평단가 유지
                    ret = ((p - avg) / avg) * 100
                    e = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f"\n   ↳ 내 수익률: {e} <b>{ret:.2f}%</b> (평단 {avg}원)"
                coin_messages.append(msg)
        # 각 코인 사이의 간격을 한 줄로 조정
        bitcoin_str = "\n".join(coin_messages)
    except Exception as e:
        bitcoin_str = f"⚠️ 코인 에러: {e}"

    # 3. 구글 뉴스 (RSS)
    news_str = ""
    if is_news_time:
        try:
            res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=10)
            root = ET.fromstring(res.content)
            items = root.findall('./channel/item')[:10]
            # 각 뉴스 사이의 간격을 한 줄로 조정
            news_list = [f"📰 <a href='{i.find('link').text}'>{html.escape(i.find('title').text)}</a>" for i in items]
            news_str = "\n".join(news_list)
        except:
            news_str = "⚠️ 뉴스 로딩 실패"

    return market_str, bitcoin_str, news_str

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    requests.post(url, data=payload)

if __name__ == "__main__":
    m, c, n = get_financial_info()
    if m or c:
        parts = []
        # 제목과 내용 사이, 그리고 각 섹션 사이를 모두 한 줄 줄바꿈(\n)으로 처리
        parts.append(f"📊 <b>[시장 주요 지표]</b>\n{m}")
        parts.append(f"🚀 <b>[가상화폐 시세]</b>\n{c}")
        if n:
            parts.append(f"🌏 <b>[구글 주요 뉴스]</b>\n{n}")
        
        # 섹션 간에도 한 줄만 띄우도록 설정
        final_message = "\n".join(parts)
        send_telegram_message(final_message)
