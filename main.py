import requests
from bs4 import BeautifulSoup
import os
from fake_useragent import UserAgent

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_headers():
    # 매번 새로운 브라우저인 척 위장하는 함수
    ua = UserAgent()
    return {'User-Agent': ua.random}

def get_exchange_rates():
    # [1] 환율 정보 가져오기
    url = "https://finance.naver.com/marketindex/"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        rates = []
        
        # 미국 USD
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            rates.append(f"🇺🇸 미국 USD: {usd.text}원")
            
        # 일본 JPY
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            rates.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
            
        return "\n".join(rates) if rates else "환율 정보 없음"
    except Exception as e:
        print(f"환율 가져오기 실패: {e}")
        return "환율 정보를 불러올 수 없음"

def get_weather_info():
    # [2] 서울 날씨 및 미세먼지 가져오기
    url = "https://search.naver.com/search.naver?query=서울+날씨"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        weather_data = []
        
        # 1. 현재 온도 (예: 5.4°)
        # '현재 온도'라는 글자를 제외하고 숫자와 기호만 가져오기 위해 slice 사용
        temp_tag = soup.select_one("div.temperature_text > strong")
        if temp_tag:
            # "현재 온도5.4°" -> "5.4°" 로 깔끔하게 정리
            current_temp = temp_tag.text.replace("현재 온도", "").strip()
            weather_data.append(f"🌡 서울 온도: {current_temp}")
        
        # 2. 미세먼지 & 초미세먼지 상태
        # 네이버 날씨 박스 안의 리스트에서 상태(좋음/보통/나쁨)를 찾습니다.
        details = soup.select("ul.today_chart_list > li")
        
        if len(details) >= 2:
            # 첫 번째 항목: 미세먼지
            fine_dust = details[0].select_one("span.txt").text
            # 두 번째 항목: 초미세먼지
            ultra_fine_dust = details[1].select_one("span.txt").text
            
            weather_data.append(f"😷 미세먼지: {fine_dust}")
            weather_data.append(f"🌫 초미세먼지: {ultra_fine_dust}")
            
        return "\n".join(weather_data) if weather_data else "날씨 정보 없음"

    except Exception as e:
        print(f"날씨 가져오기 실패: {e}")
        return "날씨 정보를 불러올 수 없음"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

if __name__ == "__main__":
    # 1. 환율 정보 가져오기
    rates_msg = get_exchange_rates()
    
    # 2. 날씨 정보 가져오기
    weather_msg = get_weather_info()
    
    # 3. 메시지 합치기
    final_message = (
        f"📅 [오늘의 정보 알림]\n\n"
        f"{weather_msg}\n\n"
        f"💰 [환율]\n"
        f"{rates_msg}"
    )
    
    # 4. 전송
    print(final_message) # 로그 확인용
    send_telegram_message(final_message)
