import os
import sys
import json
import time
import re
import requests
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# 설정 파일 경로 (절대 경로로 변경하여 오류 방지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(BASE_DIR), "지식창고", "마케팅분석", "delivery_config.json")
SYNC_FILE_PATH = r"g:\내 드라이브\킹옥션 그래비티\결과물\고객관리\synced_data.js"

# 이사님만의 전용 통로 ID
NTFY_TOPIC = "kingauction_crm_secure_bridge_2026_direct"

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def parse_customer_info(text):
    """
    텍스트에서 이름, 연락처 등을 추출하는 로직 (특수문자 및 태그 완벽 대응)
    """
    # 1. 특수 문자 및 투명 문자(\u2068, \u2069) 제거
    clean_text = text.replace("{not_title}", "").replace("{notification}", "").replace("[notification_title]", "").replace("[notification_text]", "")
    clean_text = clean_text.replace('\u2068', '').replace('\u2069', '')
    clean_text = clean_text.strip()
    
    name = "이름 미상"
    
    # 2. 이름 및 내용 분리 (콜론 또는 공백 기준)
    if " : " in clean_text:
        parts = clean_text.split(" : ", 1)
        name = parts[0].strip()
    elif ":" in clean_text:
        parts = clean_text.split(":", 1)
        name = parts[0].strip()
    else:
        # 한글 이름 추출 (2~10자 - 업체명 포함 가능성)
        name_match = re.search(r'([가-힣\.]+)', clean_text)
        if name_match:
            name = name_match.group(1)

    # 카톡 이름 형식 [홍길동] 처리
    if "[" in name and "]" in name:
        name = name.split("[")[1].split("]")[0]
        
    # 3. 연락처 추출
    phone_match = re.search(r'01[0-9]-?\d{3,4}-?\d{4}', clean_text)
    phone = phone_match.group(0) if phone_match else ""
    
    # 4. 상태 추론
    status = "interest"
    if any(kw in clean_text for kw in ["신청", "입금", "등록", "수강"]):
        status = "prospect"
    elif any(kw in clean_text for kw in ["궁금", "문의", "얼마", "위치", "장소"]):
        status = "counsel"
        
    return {
        "id": int(time.time() * 1000),
        "name": name,
        "phone": phone,
        "path": "모바일(자동)",
        "status": status,
        "memo": f"[무인수집] {clean_text[:150]}",
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def update_sync_file(new_customer):
    existing_data = []
    if os.path.exists(SYNC_FILE_PATH):
        try:
            with open(SYNC_FILE_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                json_str = re.search(r'\[.*\]', content, re.DOTALL)
                if json_str:
                    existing_data = json.loads(json_str.group(0))
        except: pass

    # 이사님 테스트를 위해 완벽히 동일한 내용이 와도 '과거' 데이터와 겹치는 것은 허용
    # 최근 5개 메시지 중에 이름과 메모가 '완전히 똑같은' 경우에만 중복 처리
    recent_data = existing_data[:5]
    is_duplicate = any(c['name'] == new_customer['name'] and c['memo'] == new_customer['memo'] for c in recent_data)

    
    if not is_duplicate:
        existing_data.insert(0, new_customer)
        existing_data = existing_data[:100]
        with open(SYNC_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"window.CRM_SYNC_DATA = {json.dumps(existing_data, ensure_ascii=False, indent=2)};")
        return True
    return False

def main():
    print(f"[START] 킹옥션 '다이렉트 통로' 수신 서버 작동 중...")
    config = load_config()
    bot_token = config.get("bot_token")
    
    # 과거 신호 소급 적용 (이사님이 보낸 테스트 확인용)
    print("[WAIT] 과거 테스트 신호 복구 중...")
    try:
        past_resp = requests.get(f"https://ntfy.sh/{NTFY_TOPIC}/json?poll=1")
        for line in past_resp.text.strip().split("\n"):
            if not line: continue
            data = json.loads(line)
            if data.get("event") == "message":
                customer = parse_customer_info(data.get("message"))
                update_sync_file(customer)
    except: pass
    
    while True:
        try:
            url = f"https://ntfy.sh/{NTFY_TOPIC}/json"
            with requests.get(url, stream=True, timeout=120) as response:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if data.get("event") == "message":
                            text = data.get("message")
                            print(f"\n[DETECT] {text[:30]}...")
                            customer = parse_customer_info(text)
                            if update_sync_file(customer):
                                print(f"[OK] CRM 업데이트 완료: {customer['name']}")
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    main()
