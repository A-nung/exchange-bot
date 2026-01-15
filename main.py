import requests
from bs4 import BeautifulSoup
import os
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# 1. 환경 설정
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
MY_SAND_AVG = 898 # 샌드박스 매수 평단가

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

    # --- 코인 ---
    try:
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
    """구글 RSS를 통한 주요 뉴스 추출"""
    news = []
    try:
        res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=10)
        root = ET.fromstring(res.content)
        items = root.findall(".//item")[:10]
        
        for i, item in enumerate(items, 1):
            title_text = item.find("title").text
            link_text = item.find("link").text
            clean_title = title_text.split(" - ")[0]
            safe_title = html.escape(clean_title)
            news.append(f"{i}. <a href='{link_text}'>{safe_title}</a>")
    except:
        news.append("⚠️ 뉴스 수집 중 오류가 발생했습니다.")
    return "\n".join(news)

def send_telegram(message):
    """텔레그램 메시지 전송"""
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    # 한국 시간(KST) 계산 (UTC + 9시간)
    now_utc = datetime.utcnow()
    now_kst = now_utc + timedelta(hours=9)
    now_str = now_kst.strftime('%m/%d %H:%M')
    
    # 1. 금융 정보는 매시간 수집
    fin_text = get_financial_info()
    
    # 2. 한국 시간 기준 오전 9시부터 3시간 간격 체크
    # (09, 12, 15, 18, 21, 00, 03, 06시)
    news_text = None
    if (now_kst.hour - 9) % 3 == 0:
        news_text = get_major_news()
    
    # 3. 메시지 조립
    final_msg = f"📅 <b>{now_str} 리포트 (KST)</b>\n\n"
    if fin_text:
        final_msg += f"{fin_text}\n"
    
    if news_text:
        final_msg += f"\n📰 <b>실시간 주요뉴스 (3시간 주기)</b>\n{news_text}"
    
    # 4. 전송
    send_telegram(final_msg)
