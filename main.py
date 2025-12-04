import requests
from bs4 import BeautifulSoup
import os

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_exchange_rates():
    # 네이버 금융 접속
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    message_list = []
    
    # 1. 미국 달러(USD) 가져오기
    usd = soup.select_one("a.head.usd > div.head_info > span.value")
    if usd:
        message_list.append(f"🇺🇸 미국 USD: {usd.text}원")
        
    # 2. 일본 엔화(JPY) 가져오기 (보통 100엔 기준입니다)
    jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
    if jpy:
        message_list.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
    
    # 줄바꿈으로 합쳐서 돌려주기
    return "\n".join(message_list)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

if __name__ == "__main__":
    rates = get_exchange_rates()
    if rates:
        print("환율 가져오기 성공")
        # 보기 좋게 제목을 달아서 보냅니다
        final_message = f"💰 [현재 환율 정보]\n\n{rates}"
        send_telegram_message(final_message)
    else:
        print("환율 정보를 가져오지 못했습니다.")
