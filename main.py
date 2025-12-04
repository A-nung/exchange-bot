import requests
from bs4 import BeautifulSoup
import os
import re # 숫자만 쏙 뽑아내기 위해 추가

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_headers():
    # PC(윈도우 크롬)인 척 위장
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }

def get_exchange_rates():
    url = "https://finance.naver.com/marketindex/"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        rates = []
        usd = soup.select_one("a.head.usd > div.head_info > span.value")
        if usd:
            rates.append(f"🇺🇸 미국 USD: {usd.text}원")
        jpy = soup.select_one("a.head.jpy > div.head_info > span.value")
        if jpy:
            rates.append(f"🇯🇵 일본 JPY (100엔): {jpy.text}원")
            
        return "\n".join(rates) if rates else "환율 정보 없음"
    except Exception as e:
        return f"환율 에러: {e}"

def get_weather_info():
    # [변경] 네이버 '검색' 대신 '날씨 전용 사이트' (서울 중구 기준) 사용
    # 해외(GitHub 서버)에서 접속해도 비교적 차단이 덜하고 구조가 일정함
    url = "https://weather.naver.com/today/09140104"
    
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        weather_data = []
        
        # 1. 현재 온도 가져오기 (strong.current 클래스)
        # 예: "현재 온도-1.5°" -> "현재 온도" 글씨 제거
        current_temp = soup.select_one("strong.current")
        if current_temp:
            temp_text = current_temp.text.replace("현재 온도", "").strip()
            weather_data.append(f"🌡 서울 온도: {temp_text}")
        else:
            # 온도를 못 찾았으면 HTML 구조가 바뀐 것임
            return "온도 정보를 찾을 수 없습니다."

        # 2. 날씨 상태 (맑음, 흐림 등)
        weather_state = soup.select_one("span.weather")
        if weather_state:
             weather_data.append(f"🌈 상태: {weather_state.text}")

        # 3. 미세먼지 정보 가져오기
        # '내일' 탭이 아니라 '오늘' 차트 정보를 가져옴
        details = soup.select("ul.today_chart_list > li")
        
        if details:
            for item in details:
                # 항목 이름 (미세먼지/초미세먼지/자외선 등)
                label = item.select_one("strong.title")
                # 값 (좋음/보통/나쁨)
                value = item.select_one("span.txt")
                
                if label and value:
                    label_text = label.text.strip()
                    if "미세먼지" in label_text: # 미세먼지, 초미세먼지만 골라냄
                        weather_data.append(f"😷 {label_text}: {value.text.strip()}")

        return "\n".join(weather_data)

    except Exception as e:
        print(f"날씨 가져오기 실패: {e}")
        return f"날씨 에러 발생: {e}"

def send_telegram_message(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
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
