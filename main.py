import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET  # XML(RSS)를 전문적으로 처리하는 도구 추가

# GitHub 금고에서 환경변수 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 1. 환율 정보 (네이버 금융 - HTML 파싱) ---
    exchange_url = "https://finance.naver.com/marketindex/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(exchange_url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")
        
        exchange_list = []
        
        # 미국 달러
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            exchange_list.append(f"🇺🇸 미국 USD: {usd.text}원")
            
        # 일본 엔화
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            exchange_list.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
            
        exchange_str = "\n".join(exchange_list)
        
    except Exception as e:
        exchange_str = f"환율 정보 에러: {e}"

    # --- 2. 구글 주요 뉴스 (RSS - XML 파싱으로 변경) ---
    google_news_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(google_news_url)
        # BeautifulSoup 대신 ElementTree를 사용하여 XML 구조를 정확히 파악
        root = ET.fromstring(response.content)
        
        news_list = []
        # channel 태그 안의 item 태그들을 찾습니다
        items = root.findall('./channel/item')
        
        # 상위 5개 뉴스만 가져오기
        for item in items[:5]:
            title = item.find('title').text
            link = item.find('link').text  # 이제 링크가 정확히 추출됩니다
            
            # 제목과 링크를 줄바꿈으로 구분
            news_list.append(f"📰 {title}\n🔗 {link}")
            
        news_str = "\n\n".join(news_list)
        
    except Exception as e:
        news_str = f"뉴스 정보 에러: {e}"

    return exchange_str, news_str

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

if __name__ == "__main__":
    rates, news = get_financial_info()
    
    if rates or news:
        print("데이터 가져오기 성공")
        
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
