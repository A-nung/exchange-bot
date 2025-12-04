import requests
from bs4 import BeautifulSoup
import os
import re  # 글자 검색(정규표현식)을 위한 도구

# GitHub 금고에서 비밀번호를 꺼내옵니다
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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

def get_fine_dust_info():
    # '서울 미세먼지' 검색 결과 페이지 사용
    url = "https://search.naver.com/search.naver?query=서울+미세먼지"
    
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # [핵심] 태그를 찾지 않고, 화면의 모든 텍스트를 가져옵니다.
        # 미국에서 접속해서 화면 모양이 바뀌어도 글자는 남아있기 때문입니다.
        page_text = soup.get_text()
        
        dust_info = []
        
        # 1. '미세먼지' 찾기 (예: "미세먼지 보통")
        # 정규식 설명: "미세먼지" 글자 뒤에 있는 단어 2~3글자(좋음/보통/나쁨)를 찾아라
        match_fine = re.search(r'미세먼지\s*([좋음보통나쁨최악]{2,})', page_text)
        if match_fine:
            dust_info.append(f"😷 미세먼지: {match_fine.group(1)}")
            
        # 2. '초미세먼지' 찾기
        match_ultra = re.search(r'초미세먼지\s*([좋음보통나쁨최악]{2,})', page_text)
        if match_ultra:
            dust_info.append(f"🌫 초미세먼지: {match_ultra.group(1)}")
            
        return "\n".join(dust_info) if dust_info else "미세먼지 정보(텍스트)를 찾을 수 없음"

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
    rates_msg = get_exchange_rates()
    dust_msg = get_fine_dust_info()
    
    final_message = (
        f"📅 [오늘의 정보 알림]\n\n"
        f"{dust_msg}\n\n"
        f"💰 [환율]\n"
        f"{rates_msg}"
    )
    
    print(final_message)
    send_telegram_message(final_message)
