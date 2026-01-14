import requests
from bs4 import BeautifulSoup
import os
import html
import xml.etree.ElementTree as ET  # XML 처리를 위한 내장 라이브러리
from datetime import datetime

# 1. 환경 설정
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') 
CHAT_ID = os.environ.get('CHAT_ID')               
MY_SAND_AVG = 898                                 

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def get_financial_info():
    """환율 및 코인(BTC, ETH, XRP, SAND) 시세 요약"""
    lines = []
    # --- 환율 ---
    try:
        res = requests.get("https://finance.naver.com/marketindex/", headers=HEADERS, timeout=10)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, "html.parser")
        usd = soup.select_one("a.head.usd span.value").text
        jpy = soup.select_one("a.head.jpy span.value").text
        lines.append(f"💵 USD <b>{usd}</b> | 💴 JPY <b>{jpy}</b>")
    except: pass

    # --- 코인 (BTC, ETH, XRP, SAND 포함) ---
    try:
        # 업비트 API에서 리플(XRP)을 포함하여 호출
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND", timeout=10).json()
        c = {i['market']: i for i in res}
        
        targets = [('KRW-BTC','🟠','BTC'), ('KRW-ETH','💠','ETH'), ('KRW-XRP','🌊','XRP'), ('KRW-SAND','🏖️','SAND')]
        
        for m, icon, name in targets:
            if m in c:
                p, r = c[m]['trade_price'], c[m]['signed_change_rate'] * 100
                txt = f"{icon} {name}: <b>{p:,}</b> ({'+' if r>0 else ''}{r:.1f}%)"
                if m == 'KRW-SAND':
                    yield_rate = ((p - MY_SAND_AVG) / MY_SAND_AVG) * 100
                    txt += f" [수익 <b>{yield_rate:.1f}%</b>]"
                lines.append(txt)
    except: pass
    return "\n".join(lines)

def get_major_news():
    """뉴스 링크를 정확하게 추출하여 클릭 가능한 형태로 반환"""
    news = []
    try:
        res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=10)
        # BeautifulSoup 대신 내장 XML 파서 사용 (링크 추출 정확도 100%)
        root = ET.fromstring(res.content)
        items = root.findall(".//item")[:10]
        
        for i, item in enumerate(items, 1):
            title_text = item.find("title").text
            link_text = item.find("link").text
            
            # 제목에서 언론사 분리 및 특수문자 처리
            clean_title = title_text.split(" - ")[0]
            safe_title = html.escape(clean_title)
            
            # 텔레그램에서 클릭 가능한 <a> 태그 생성
            news.append(f"{i}. <a href='{link_text}'>{safe_title}</a>")
    except:
        news.append("⚠️ 뉴스 수집 중 오류가 발생했습니다.")
    return "\n".join(news)

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML', # HTML 모드 활성화 필수
        'disable_web_page_preview': True
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    now = datetime.now().strftime('%m/%d %H:%M')
    fin_text = get_financial_info()
    news_text = get_major_news()
    
    # 불필요한 공백을 제거한 콤팩트한 레이아웃
    final_msg = f"📅 <b>{now} 리포트</b>\n\n"
    if fin_text:
        final_msg += f"{fin_text}\n"
    final_msg += f"\n📰 <b>실시간 주요뉴스</b>\n{news_text}"
    
    send_telegram(final_msg)
