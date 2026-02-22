import os
import json
import time
import re
import requests
from datetime import datetime

# 설정 파일 경로
CONFIG_PATH = r"g:\내 드라이브\킹옥션 그래비티\지식창고\마케팅분석\delivery_config.json"
SYNC_FILE_PATH = r"g:\내 드라이브\킹옥션 그래비티\결과물\고객관리\synced_data.js"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_customer_info(text):
    """
    텍스트에서 이름, 연락처 등을 추출하는 로직 (모바일 알림 포맷 최적화)
    """
    # 1. 이름 추출 전략
    name = "이름 미상"
    
    # 카톡 알림 패턴: "[이름] 메시지" 또는 "이름: 메시지"
    kakao_pattern = re.search(r'\[([^\]]+)\]', text)
    colon_pattern = re.search(r'^([^:]+):', text)
    
    if kakao_pattern:
        name = kakao_pattern.group(1)
    elif colon_pattern:
        name = colon_pattern.group(1).strip()
    else:
        # 일반 한글 이름 (2~4자) 탐색
        name_match = re.search(r'([가-힣]{2,4})', text)
        if name_match:
            name = name_match.group(1)
    
    # 2. 연락처 추출 (010-1234-5678 또는 01012345678)
    phone_match = re.search(r'01[0-9]-?\d{3,4}-?\d{4}', text)
    phone = phone_match.group(0) if phone_match else ""
    
    # 3. 유입 경로 및 단계 추론
    status = "interest"
    if any(kw in text for kw in ["신청", "입금", "등록", "수강"]):
        status = "prospect"
    elif any(kw in text for kw in ["궁금", "문의", "얼마", "위치", "장소"]):
        status = "counsel"
        
    return {
        "id": int(time.time() * 1000),
        "name": name,
        "phone": phone,
        "path": "모바일(자동)",
        "status": status,
        "memo": f"[자동수집] {text[:150]}",
        "date": datetime.now().strftime("%Y-%m-%d")
    }

def update_sync_file(new_customer):
    """
    JS 파일을 업데이트하여 CRM 대시보드에서 읽을 수 있게 함
    """
    existing_data = []
    if os.path.exists(SYNC_FILE_PATH):
        try:
            with open(SYNC_FILE_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                # window.CRM_SYNC_DATA = [...]; 에서 [...] 부분만 추출
                json_str = re.search(r'\[.*\]', content, re.DOTALL)
                if json_str:
                    existing_data = json.loads(json_str.group(0))
        except Exception as e:
            print(f"기존 파일 읽기 오류: {e}")

    # 중복 제거 (이름과 번호가 같으면 제외 - 간단하게)
    is_duplicate = any(c['name'] == new_customer['name'] and c['phone'] == new_customer['phone'] for c in existing_data)
    
    if not is_duplicate:
        existing_data.insert(0, new_customer)
        # 최대 50개까지만 유지
        existing_data = existing_data[:50]
        
        with open(SYNC_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"window.CRM_SYNC_DATA = {json.dumps(existing_data, ensure_ascii=False, indent=2)};")
        return True
    return False

def main():
    config = load_config()
    bot_token = config["bot_token"]
    target_chat_id = int(config["chat_id"])
    last_update_id = 0
    
    print(f"CRM 텔레그램 동기화 봇 시작... (Target ID: {target_chat_id})")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url).json()
            
            if "result" in response:
                for update in response["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        
                        # 모든 채팅방 입력을 실시간으로 모니터링 (연동 확인용)
                        text = msg.get("text") or msg.get("caption")
                        if text:
                            print(f"\n[신호 감지] (ID: {chat_id}) {text[:20]}...")
                            customer = parse_customer_info(text)
                            if update_sync_file(customer):
                                print(f"✅ CRM 동기화 완료: {customer['name']}")
                                try:
                                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                                                 json={"chat_id": chat_id, "text": f"✅ CRM에 기록되었습니다: {customer['name']}"})
                                except:
                                    pass
            
        except Exception as e:
            print(f"오류 발생: {e}")
            time.sleep(5)
        
        time.sleep(1)

if __name__ == "__main__":
    main()
