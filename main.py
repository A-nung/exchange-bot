import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

# 1. 환경 설정
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') 
CHAT_ID = os.environ.get('CHAT_ID')               
MY_SAND_AVG = 898                                 

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}

def get_financial_info():
    """환율 및 코인 시세를 요약된 텍스트로 반환"""
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
        
        for m, icon, name in [('KRW-BTC','🟠','BTC'), ('KRW-ETH','💠','ETH'), ('KRW-SAND','🏖️','SAND')]:
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
    """주요 뉴스 10개를 번호와 링크로 반환"""
    news = []
    try:
        # html.parser를 사용하여 추가 라이브러리 에러 방지
        res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.find_all("item")[:10]
        
        for i, item in enumerate(items, 1):
            title = item.title.get_text()
            link = item.link.get_text()
            # 제목 뒤의 언론사 정보 분리 시도 (보안 및 가독성)
            news.append(f"{i}. <a href='{link}'>{title}</a>")
    except:
        news.append("⚠️ 뉴스 수집 불가")
    return "\n".join(news)

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': True})

if __name__ == "__main__":
    now = datetime.now().strftime('%m/%d %H:%M')
    fin_text = get_financial_info()
    news_text = get_major_news()
    
    # 가독성을 극대화한 최종 메시지 구성
    final_msg = f"📅 <b>{now} 리포트</b>\n\n"
    if fin_text:
        final_msg += f"{fin_text}\n"
    final_msg += f"\n📰 <b>실시간 주요뉴스</b>\n{news_text}"
    
    send_telegram(final_msg)
