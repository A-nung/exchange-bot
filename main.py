import requests
from bs4 import BeautifulSoup
import os
from fake_useragent import UserAgent  # 랜덤 헤더 생성 도구

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_exchange_rates():
    url = "https://finance.naver.com/marketindex/"
    
    # 1. 가짜 유저 에이전트 객체 생성
    ua = UserAgent()
    
    # 2. ua.random을 호출하면 매번 다른 브라우저/OS 정보를 줍니다 (완전 랜덤)
    headers = {
        'User-Agent': ua.random
    }

    try:
        # 랜덤 헤더를 달고 요청 전송
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 접속 에러(404, 500 등) 체크
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        message_list = []
        
        # 1. 미국 달러(USD) 가져오기
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            message_list.append(f"🇺🇸 미국 USD: {usd.text}원")
            
        # 2. 일본 엔화(JPY) 가져오기 (100엔 기준)
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            message_list.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
        
        # 정보가 없으면 None 반환
        if not message_list:
            return None
            
        return "\n".join(message_list)

    except Exception as e:
        # 에러 발생 시 로그만 남기고 봇이 멈추지 않게 함
        print(f"환율 정보를 가져오는 중 에러 발생: {e}")
        return None

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("텔레그램 토큰이나 CHAT_ID가 설정되지 않았습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"메시지 전송 실패: {response.text}")
    except Exception as e:
        print(f"전송 중 에러 발생: {e}")

if __name__ == "__main__":
    rates = get_exchange_rates()
    
    if rates:
        print("환율 가져오기 성공")
        final_message = f"💰 [현재 환율 정보]\n\n{rates}"
        send_telegram_message(final_message)
    else:
        print("환율 정보를 가져오지 못했습니다.")
