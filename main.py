import requests
from bs4 import BeautifulSoup
import os

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_headers():
    # 중요: 모바일 User-Agent가 걸리면 HTML 구조가 달라지므로
    # 반드시 PC 버전(윈도우/크롬)으로 고정해야 합니다.
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

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
        
        # 1. 현재 온도
        temp_tag = soup.select_one("div.temperature_text > strong")
        if temp_tag:
            # "현재 온도5.4°" 에서 "현재 온도" 글자 제거
            current_temp = temp_tag.text.replace("현재 온도", "").strip()
            weather_data.append(f"🌡 서울 온도: {current_temp}")
        
        # 2. 미세먼지 & 초미세먼지
        # PC 버전 네이버 검색 결과 기준 선택자
        details = soup.select("ul.today_chart_list > li")
        
        if len(details) >= 2:
            fine_dust = details[0].select_one("span.txt").text # 미세먼지
            ultra_fine_dust = details[1].select_one("span.txt").text # 초미세먼지
            
            weather_data.append(f"😷 미세먼지: {fine_dust}")
            weather_data.append(f"🌫 초미세먼지: {ultra_fine_dust}")
        
        # 만약 정보를 하나도 못 찾았다면
        if not weather_data:
            return "날씨 정보를 찾을 수 없음 (HTML 구조 변경됨)"
            
        return "\n".join(weather_data)

    except Exception as e:
        print(f"날씨 가져오기 실패: {e}")
        return f"날씨 에러 발생: {e}"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("토큰 설정 오류")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"전송 실패: {e}")

if __name__ == "__main__":
    rates_msg = get_exchange_rates()
    weather_msg = get_weather_info()
    
    final_message = (
        f"📅 [오늘의 정보 알림]\n\n"
        f"{weather_msg}\n\n"
        f"💰 [환율]\n"
        f"{rates_msg}"
    )
    
    print(final_message)
    send_telegram_message(final_message)
