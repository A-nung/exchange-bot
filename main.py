import requests
from bs4 import BeautifulSoup
import os

# GitHub가 보관 중인 비밀번호(토큰)를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_exchange_rate():
    # 네이버 금융 접속
    url = "https://finance.naver.com/marketindex/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    # 환율 정보 찾기
    market_data = soup.select_one("a.head.usd > div.head_info > span.value")
    return market_data.text if market_data else None

def send_telegram_message(message):
    # 텔레그램 전송
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

if __name__ == "__main__":
    rate = get_exchange_rate()
    if rate:
        print(f"환율 가져오기 성공: {rate}")
        send_telegram_message(f"💰 현재 원/달러 환율: {rate}원")
    else:
        print("환율 정보를 가져오지 못했습니다.")
