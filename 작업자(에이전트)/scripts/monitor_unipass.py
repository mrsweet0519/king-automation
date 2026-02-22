import os
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import requests

# 설정 파일 경로
CONFIG_PATH = "g:/내 드라이브/킹옥션 그래비티/지식창고/마케팅분석/delivery_config.json"
STATE_PATH = "g:/내 드라이브/킹옥션 그래비티/지식창고/마케팅분석/unipass_last_notice.json"

async def get_latest_notice():
    """
    유니패스 사이트에 접속하여 최신 체화공매 공고 정보를 가져옵니다.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        try:
            # 1. 유니패스 접속
            await page.goto("https://unipass.customs.go.kr/csp/index.do", wait_until="networkidle", timeout=60000)
            
            # 2. 메뉴 이동 (업무지원 -> 체화공매 -> 체화공매안내)
            # 텍스트로 메뉴를 찾는 방식이 가장 직관적입니다.
            await page.click("text='업무지원'")
            await asyncio.sleep(1)
            await page.click("text='체화공매'")
            await asyncio.sleep(1)
            await page.click("text='체화공매안내'")
            
            # 3. 테이블 로딩 대기
            table_selector = "#MYC0202001Q_tableLst"
            await page.wait_for_selector(table_selector, timeout=30000)
            
            # 4. 첫 번째 행 데이터 추출 (세관명, 공고일자, 공고명)
            first_row = page.locator(f"{table_selector} tbody tr").first
            customs_name = await first_row.locator("td").nth(1).inner_text()
            notice_date = await first_row.locator("td").nth(4).inner_text()
            notice_title = await first_row.locator("td").nth(5).inner_text()
            
            return {
                "id": f"{customs_name}_{notice_date}_{notice_title.replace(' ', '')}",
                "customs": customs_name.strip(),
                "date": notice_date.strip(),
                "title": notice_title.strip()
            }
        except Exception as e:
            print(f"유니패스 데이터 추출 도중 오류 발생: {e}")
            return None
        finally:
            await browser.close()

def send_telegram(token, chat_id, text):
    """텔레그램 메시지 발송"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"텔레그램 발송 오류: {e}")

async def main():
    # 1. 설정 및 이전 상태 로드
    if not os.path.exists(CONFIG_PATH) or not os.path.exists(STATE_PATH):
        print("설정 파일 또는 상태 파일이 없습니다.")
        return

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    # 2. 최신 공고 가져오기
    print(f"[{datetime.now()}] 유니패스 체크 중...")
    latest = await get_latest_notice()
    
    if latest:
        print(f"현재 최신 공고: {latest['title']} ({latest['date']})")
        
        # 3. 이전 공고와 비교
        if latest["id"] != state.get("last_notice_id"):
            print("새로운 공고 발견! 알림을 보냅니다.")
            
            msg = (
                f"🔔 *[유니패스 신규 공매 공고]*\n\n"
                f"📍 **세관명**: {latest['customs']}\n"
                f"📅 **공고일**: {latest['date']}\n"
                f"📝 **공고명**: {latest['title']}\n\n"
                f"🔗 [유니패스 바로가기](https://unipass.customs.go.kr/csp/index.do)"
            )
            
            send_telegram(config["bot_token"], config["chat_id"], msg)
            
            # 4. 상태 업데이트
            state["last_notice_id"] = latest["id"]
            state["last_notice_title"] = latest["title"]
            state["last_notice_date"] = latest["date"]
            state["last_check_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        else:
            print("새로운 공고가 없습니다.")
            state["last_check_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
