import requests
from bs4 import BeautifulSoup
import os

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 1. 환율 정보 가져오기 (네이버 금융) ---
    exchange_url = "https://finance.naver.com/marketindex/"
    # 봇 차단을 막기 위해 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(exchange_url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        exchange_list = []
        
        # 미국 달러(USD)
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            exchange_list.append(f"🇺🇸 미국 USD: {usd.text}원")
            
        # 일본 엔화(JPY)
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            exchange_list.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
            
        exchange_str = "\n".join(exchange_list)
        
    except Exception as e:
        exchange_str = f"환율 정보 가져오기 실패: {e}"

    # --- 2. 구글 주요 뉴스 가져오기 (RSS 활용) ---
    # 구글 뉴스 대한민국 주요 뉴스 RSS 주소
    google_news_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(google_news_url)
        # XML 형식이지만 html.parser로도 item 태그를 찾을 수 있습니다.
        soup = BeautifulSoup(response.content, "html.parser")
        
        news_list = []
        # item 태그가 각각의 뉴스 기사입니다.
        items = soup.select("item")
        
        for item in items[:10]:  # 상위 10개 뉴스만 추출
            title = item.title.text
            link = item.link.text if item.link else ""
            
            # 구글 뉴스 RSS는 제목에 매체명이 포함되는 경우가 많아 깔끔하게 정리 가능
            news_list.append(f"📰 {title}\n🔗 {link}")
            
        news_str = "\n\n".join(news_list)
        
    except Exception as e:
        news_str = f"뉴스 가져오기 실패: {e}"

    return exchange_str, news_str

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

if __name__ == "__main__":
    rates, news = get_financial_info()
    
    # 메시지 내용이 있을 때만 전송
    if rates or news:
        print("데이터 가져오기 완료")
        
        final_message = (
            f"💰 [현재 환율 정보]\n"
            f"{rates}\n\n"
            f"--------------------\n\n"
            f"🌏 [구글 주요 뉴스]\n"
            f"{news}"
        )
        
        send_telegram_message(final_message)
    else:
        print("데이터를 가져오지 못했습니다.")
