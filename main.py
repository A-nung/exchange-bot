import requests
from bs4 import BeautifulSoup
import os
import html 
from datetime import datetime, timedelta, timezone

# ------------------------------------------------
# 1. 환경 설정 및 상수 정의 
# ------------------------------------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')  # 텔레그램 봇 토큰
CHAT_ID = os.environ.get('CHAT_ID')                # 메시지를 받을 채팅 ID
MY_SAND_AVG = 898                                  # 샌드박스(SAND) 개인 평단가 

# HTTP 요청 시 사용할 헤더 (봇 차단 방지) 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_financial_info():
    """금융 지표, 코인 시세, 네이버 뉴스를 수집하여 반환합니다."""
    
    # 한국 시간(KST) 설정 
    kst_tz = timezone(timedelta(hours=9))
    kst_now = datetime.now(kst_tz)
    current_hour = kst_now.hour
    
    # 뉴스 발송 여부 결정 (3시간 간격) 
    is_news_time = (current_hour % 3 == 0)

    # ------------------------------------------------
    # 2. 주요 환율 정보 수집 (네이버 금융) 
    # ------------------------------------------------
    market_list = []
    try:
        url = "https://finance.naver.com/marketindex/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'euc-kr'  # 네이버 금융 인코딩 대응 
        soup = BeautifulSoup(res.text, "html.parser")
        
        usd = soup.select_one("a.head.usd span.value")
        if usd: market_list.append(f"💵 미국 USD: <b>{usd.text}원</b>")
            
        jpy = soup.select_one("a.head.jpy span.value")
        if jpy: market_list.append(f"💴 일본 JPY (100엔): <b>{jpy.text}원</b>")
    except Exception:
        market_list.append("⚠️ 환율 정보를 가져오지 못했습니다.")
    market_str = "\n".join(market_list)

    # ------------------------------------------------
    # 3. 가상화폐 시세 수집 (Upbit API) 
    # ------------------------------------------------
    coin_messages = []
    try:
        upbit_url = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH,KRW-XRP,KRW-SAND"
        res = requests.get(upbit_url, timeout=10).json()
        coin_data = {item['market']: item for item in res}
        
        # 출력 대상 정의 (마켓ID, 아이콘, 이름)
        targets = [
            ('KRW-BTC', '🟠', '비트코인 (BTC)'),
            ('KRW-ETH', '💠', '이더리움 (ETH)'),
            ('KRW-XRP', '🌊', '리플 (XRP)'),
            ('KRW-SAND', '🏖️', '샌드박스 (SAND)')
        ]
        
        for m_id, icon, name in targets:
            if m_id in coin_data:
                d = coin_data[m_id]
                price = d['trade_price']
                change = d['signed_change_rate']
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "-"
                
                msg = f"{icon} <b>{name}</b>\n현재가: <b>{price:,}원</b> ({emoji} {change*100:.2f}%)"
                
                # 샌드박스 전용 수익률 계산 
                if m_id == 'KRW-SAND':
                    ret = ((price - MY_SAND_AVG) / MY_SAND_AVG) * 100
                    re_emoji = "🔥" if ret > 0 else "💧" if ret < 0 else "-"
                    msg += f"\n      ↳ 수익률: {re_emoji} <b>{ret:.2f}%</b>"
                
                coin_messages.append(msg)
    except Exception:
        coin_messages.append("⚠️ 코인 시세를 가져오지 못했습니다.")
    bitcoin_str = "\n\n".join(coin_messages)

    # ------------------------------------------------
    # 4. 네이버 뉴스 전 섹션 수집 (정치~IT)
    # ------------------------------------------------
    naver_news_parts = []
    if is_news_time:
        # 뉴스 섹션별 코드 (정치:100, 경제:101, 사회:102, 생활:103, 세계:104, IT:105)
        sections = {"정치": 100, "경제": 101, "사회": 102, "생활": 103, "세계": 104, "IT": 105}
        
        for name, sid in sections.items():
            try:
                url = f"https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1={sid}"
                res = requests.get(url, headers=HEADERS, timeout=10)
                soup = BeautifulSoup(res.text, "html.parser")
                
                # 헤드라인 뉴스 5개 추출
                items = soup.select(".sh_text_headline, .cjs_t")[:5]
                links = []
                for i, item in enumerate(items, 1):
                    title = item.get_text().strip()
                    # 상위 <a> 태그 탐색
                    anchor = item.find_parent("a") or item.select_one("a")
                    link = anchor["href"] if anchor else "#"
                    links.append(f"  {i}. <a href='{link}'>{title}</a>")
                
                if links:
                    naver_news_parts.append(f"📌 <b>{name} 주요뉴스</b>\n" + "\n\n".join(links))
            except:
                continue
    naver_news_str = "\n\n\n".join(naver_news_parts)

    return market_str, bitcoin_str, naver_news_str

def send_telegram_message(message):
    """최종 구성된 메시지를 텔레그램으로 전송합니다. """
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID, 
        'text': message, 
        'parse_mode': 'HTML', 
        'disable_web_page_preview': True
    }
    requests.post(url, data=payload)

# ------------------------------------------------
# 5. 메인 실행 로직
# ------------------------------------------------
if __name__ == "__main__":
    exchange, coins, news = get_financial_info()
    
    # 메시지 섹션 구성 (가독성을 위한 세 줄 바꿈 적용) 
    final_parts = []
    if exchange:
        final_parts.append(f"📊 <b>[주요 환율 정보]</b>\n{exchange}")
    if coins:
        final_parts.append(f"🚀 <b>[가상화폐 시세]</b>\n\n{coins}")
    if news:
        final_parts.append(f"📰 <b>[네이버 섹션별 주요 뉴스]</b>\n\n{news}")
    
    if final_parts:
        # 섹션 사이 간격 최적화 (\n\n\n) 
        send_telegram_message("\n\n\n".join(final_parts))
