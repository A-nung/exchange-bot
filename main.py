import requests
from bs4 import BeautifulSoup
import os

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_headers():
    # 네이버가 봇을 차단하지 않도록 '윈도우 PC'인 척 위장합니다.
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
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
        return f"환율 에러: {e}"

def get_fine_dust_info():
    # [2] 미세먼지 정보 가져오기 (서울 중구 기준)
    url = "https://weather.naver.com/today/09140104"
    
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        dust_data = []
        
        # '오늘' 탭의 하단 차트 리스트에서 미세먼지 정보 추출
        details = soup.select("ul.today_chart_list > li")
        
        if details:
            for item in details:
                label = item.select_one("strong.title") # 항목 이름 (미세먼지 등)
                value = item.select_one("span.txt")     # 값 (좋음/보통 등)
                
                if label and value:
                    label_text = label.text.strip()
                    # '미세먼지'나 '초미세먼지'라는 글자가 포함된 경우만 가져옴
                    if "미세먼지" in label_text:
                        dust_data.append(f"😷 {label_text}: {value.text.strip()}")

        return "\n".join(dust_data) if dust_data else "미세먼지 정보 없음"

    except Exception as e:
        print(f"미세먼지 가져오기 실패: {e}")
        return f"에러 발생: {e}"

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
    # 1. 환율 정보
    rates_msg = get_exchange_rates()
    
    # 2. 미세먼지 정보 (온도 삭제됨)
    dust_msg = get_fine_dust_info()
    
    # 3. 메시지 합치기
    final_message = (
        f"📅 [오늘의 정보 알림]\n\n"
        f"{dust_msg}\n\n"
        f"💰 [환율]\n"
        f"{rates_msg}"
    )
    
    print(final_message)
    send_telegram_message(final_message)
