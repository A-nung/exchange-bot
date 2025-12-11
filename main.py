import requests
from bs4 import BeautifulSoup
import os
import xml.etree.ElementTree as ET
import html # 특수문자 처리를 위해 추가

# GitHub 금고에서 환경변수 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_financial_info():
    # --- 1. 환율 정보 (네이버 금융) ---
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
            exchange_list.append(f"🇺🇸 미국 USD: <b>{usd.text}원</b>") # 굵게 표시
            
        # 일본 엔화
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            exchange_list.append(f"🇯🇵 일본 JPY (100엔): <b>{jpy.text}원</b>") # 굵게 표시
            
        exchange_str = "\n".join(exchange_list)
        
    except Exception as e:
        exchange_str = f"환율 정보 에러: {e}"

    # --- 2. 구글 주요 뉴스 (제목에 링크 심기) ---
    google_news_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(google_news_url)
        root = ET.fromstring(response.content)
        
        news_list = []
        items = root.findall('./channel/item')
        
        for item in items[:20]:
            # 제목에 <, > 같은 특수문자가 있을 수 있어 안전하게 변환
            title = html.escape(item.find('title').text)
            link = item.find('link').text
            
            # HTML 태그 <a href="...">를 사용하여 제목에 링크를 겁니다.
            news_list.append(f"📰 <a href='{link}'>{title}</a>")
            
        news_str = "\n\n".join(news_list)
        
    except Exception as e:
        news_str = f"뉴스 정보 에러: {e}"

    return exchange_str, news_str

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # parse_mode='HTML'을 추가해야 링크가 작동합니다.
    # disable_web_page_preview=True를 넣으면 링크 미리보기 이미지를 꺼서 더 깔끔하게 만듭니다.
    data = {
        'chat_id': CHAT_ID, 
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True 
    }
    requests.post(url, data=data)

if __name__ == "__main__":
    rates, news = get_financial_info()
    
    if rates or news:
        print("데이터 가져오기 성공")
        
        final_message = (
            f"💰 <b>[현재 환율 정보]</b>\n"
            f"{rates}\n\n"
            f"--------------------\n\n"
            f"🌏 <b>[구글 주요 뉴스]</b>\n"
            f"{news}"
        )
        
        send_telegram_message(final_message)
    else:
        print("데이터를 가져오지 못했습니다.")
