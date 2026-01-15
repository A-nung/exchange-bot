import requests
from bs4 import BeautifulSoup
import os
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import logging

# 로깅 설정: 에러 발생 시 로그를 남겨 디버깅을 용이하게 함
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 1. 환경 설정 및 사용자 변수
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
MY_SAND_AVG = 898  # 사용자의 요청에 따라 하드코딩 유지 

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_financial_info():
    """환율 및 코인(BTC, ETH, XRP, SAND) 시세 요약"""
    lines = []
    
    # --- 환율 수집 ---
    try:
        res = requests.get("https://finance.naver.com/marketindex/", headers=HEADERS, timeout=15)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, "html.parser")
        
        usd = soup.select_one("a.head.usd span.value").text
        jpy = soup.select_one("a.head.jpy span.value").text
        lines.append(f"💵 USD <b>{usd}</b> | 💴 JPY <b>{jpy}</b>")
    except Exception as e:
        logger.error(f"환율 수집 중 오류 발생: {e}")
        lines.append("⚠️ 환율 정보를 불러올 수 없습니다.")

    # --- 코인 시세 수집 ---
    try:
        # 업비트 API 호출 
        res = requests.get("https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND", timeout=15).json()
        c = {i['market']: i for i in res}
        
        targets = [
            ('KRW-BTC', '🟠', 'BTC'), 
            ('KRW-ETH', '💠', 'ETH'), 
            ('KRW-XRP', '🌊', 'XRP'), 
            ('KRW-SAND', '🏖️', 'SAND')
        ]
        
        for m, icon, name in targets:
            if m in c:
                p = c[m]['trade_price']
                r = c[m]['signed_change_rate'] * 100
                txt = f"{icon} {name}: <b>{p:,}</b> ({'+' if r > 0 else ''}{r:.1f}%)"
                
                if m == 'KRW-SAND':
                    yield_rate = ((p - MY_SAND_AVG) / MY_SAND_AVG) * 100
                    txt += f" [수익 <b>{yield_rate:.1f}%</b>]"
                lines.append(txt)
    except Exception as e:
        logger.error(f"코인 시세 수집 중 오류 발생: {e}")
        lines.append("⚠️ 코인 시세를 불러올 수 없습니다.")
        
    return "\n".join(lines)

def get_major_news():
    """구글 RSS를 통한 주요 뉴스 추출 (최대 8개로 제한하여 메시지 길이 최적화)"""
    news = []
    try:
        res = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", timeout=15)
        root = ET.fromstring(res.content)
        items = root.findall(".//item")[:8] # 메시지 길이를 고려해 8개로 조정 
        
        for i, item in enumerate(items, 1):
            title_text = item.find("title").text
            link_text = item.find("link").text
            # 제목 뒤의 언론사 정보 분리 및 HTML 이스케이프 처리 
            clean_title = html.escape(title_text.split(" - ")[0])
            news.append(f"{i}. <a href='{link_text}'>{clean_title}</a>")
    except Exception as e:
        logger.error(f"뉴스 수집 중 오류 발생: {e}")
        news.append("⚠️ 실시간 뉴스를 가져오는 데 실패했습니다.")
    return "\n".join(news)

def send_telegram(message):
    """텔레그램 메시지 전송"""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.warning("TELEGRAM_TOKEN 또는 CHAT_ID가 설정되지 않았습니다.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    try:
        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"텔레그램 전송 실패: {e}")

if __name__ == "__main__":
    # 1. 시간 설정 (Python 3.12+ 대응: utcnow 대신 timezone.utc 사용) 
    now_kst = datetime.now(timezone.utc) + timedelta(hours=9)
    now_str = now_kst.strftime('%m/%d %H:%M')
    
    # 2. 금융 정보 수집
    fin_text = get_financial_info()
    
    # 3. 뉴스 수집 조건 체크 (3시간 주기)
    # GitHub Actions의 실행 지연을 고려하여 정시가 아닌 범위로 체크하거나 
    # 단순 나머지 연산을 사용하되 로깅 강화
    news_text = None
    if (now_kst.hour - 9) % 3 == 0:
        news_text = get_major_news()
    
    # 4. 메시지 조립
    final_msg = f"📅 <b>{now_str} 리포트 (KST)</b>\n\n"
    if fin_text:
        final_msg += f"{fin_text}\n"
    
    if news_text:
        final_msg += f"\n📰 <b>실시간 주요뉴스 (3시간 주기)</b>\n{news_text}"
    
    # 5. 전송
    send_telegram(final_msg)
