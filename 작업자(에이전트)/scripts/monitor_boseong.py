import os
import json
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import requests

# 설정 파일 경로 (로컬 실행용 기본값, GitHub Actions에서는 os.environ 사용)
CONFIG_PATH = os.environ.get("DELIVERY_CONFIG_PATH", "delivery_config.json")
STATE_PATH = os.environ.get("STATE_PATH", "boseong_last_notice.json")

async def get_latest_notice():
    """
    보성유통 사이트에 접속하여 최신 입찰 공고 정보를 가져옵니다.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        await Stealth().apply_stealth_async(context)
        page = await context.new_page()
        
        try:
            # 1. 보성유통 접속
            print(f"[{datetime.now()}] 보성유통 접속 시도 (URL: https://auction.utong.or.kr/page/main.php)")
            await page.goto("https://auction.utong.or.kr/page/main.php", wait_until="load", timeout=60000)
            
            # 조금 더 기다려줌 (동적 로딩 대응)
            await asyncio.sleep(5)
            
            # 2. 첫 번째 공고 추출
            target_selector = ".list_area li"
            print(f"[{datetime.now()}] 리스트 대기 중: {target_selector}")
            
            try:
                await page.wait_for_selector(target_selector, timeout=30000)
            except Exception as e:
                print(f"리스트 대기 중 타임아웃 발생. 현재 페이지 소스 일부:")
                source = await page.content()
                print(source[:1000])
                raise e

            # 상세 셀렉터로 접근
            title_selector = ".subject a"
            notice_element = page.locator(".list_area li").first.locator(title_selector)
            
            title = await notice_element.get_attribute("title")
            if not title:
                title = await notice_element.inner_text()
            
            link = await notice_element.get_attribute("href")
            
            # GG_NO 파라미터를 고유 ID로 활용
            import re
            gg_no_match = re.search(r"GG_NO=([^&]+)", link)
            notice_id = gg_no_match.group(1) if gg_no_match else link
            
            return {
                "id": notice_id.strip(),
                "title": title.strip(),
                "url": f"https://auction.utong.or.kr/page/{link.replace('./', '')}"
            }
        except Exception as e:
            print(f"보성유통 데이터 추출 도중 오류 발생: {e}")
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
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    
    # GitHub Actions 환경 변수(Secrets) 우선 적용
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("bot_token")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("chat_id")
    
    if not bot_token or not chat_id:
        print("설정 오류: 텔레그램 토큰 또는 Chat ID가 없습니다.")
        return

    state = {}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        print("상태 파일이 없어 새로 생성합니다.")

    # 2. 최신 공고 가져오기
    print(f"[{datetime.now()}] 보성유통 체크 중...")
    latest = await get_latest_notice()
    
    if latest:
        print(f"현재 최신 공고: {latest['title']} (ID: {latest['id']})")
        
        # 3. 이전 공고와 비교
        if latest["id"] != state.get("last_notice_id"):
            print("새로운 공고 발견! 알림을 보냅니다.")
            
            msg = (
                f"🔔 *[보성유통 신규 입찰 공고]*\n\n"
                f"📝 **공고명**: {latest['title']}\n"
                f"🆔 **공고번호**: {latest['id']}\n\n"
                f"🔗 [공조 상세 보기]({latest['url']})"
            )
            
            send_telegram(bot_token, chat_id, msg)
            
            # 4. 상태 업데이트
            state["last_notice_id"] = latest["id"]
            state["last_notice_title"] = latest["title"]
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
