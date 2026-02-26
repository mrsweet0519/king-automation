import os
import requests
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# 킹옥션 대표님 보고서 발송 시스템 (Telegram & Email Version)

def send_telegram_report(bot_token, chat_id, message, file_path=None):
    """
    텔레그램으로 텍스트 보고서와 대시보드 파일을 전송합니다.
    """
    base_url = f"https://api.telegram.org/bot{bot_token}"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        res = requests.post(f"{base_url}/sendMessage", data=payload)
        if res.status_code != 200:
            print(f"메시지 발송 실패: {res.text}")
            return False
            
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                files = {'document': f}
                payload = {'chat_id': chat_id}
                res_file = requests.post(f"{base_url}/sendDocument", data=payload, files=files)
                if res_file.status_code != 200:
                    print(f"파일 발송 실패: {res_file.text}")
                    return False
        return True
    except Exception as e:
        print(f"텔레그램 발송 중 네트워크 오류: {e}")
        return False

def send_email_report(smtp_server, smtp_port, sender_email, sender_password, receiver_email, subject, body, file_path=None):
    """
    이메일(SMTP)로 보고서를 전송합니다.
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(file_path)}")
                msg.attach(part)
        except Exception as e:
            print(f"파일 첨부 실패: {e}")

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"이메일 발송 실패: {e}")
        return False

if __name__ == "__main__":
    # 설정 파일 경로 (로컬용) 또는 환경 변수 사용
    CONFIG_PATH = os.environ.get("DELIVERY_CONFIG_PATH", "g:/내 드라이브/킹옥션 그래비티/지식창고/마케팅분석/delivery_config.json")
    
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
    # 환경 변수 우선 적용
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("bot_token")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("chat_id")
    
    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]
    
    # 요일별 동적 브리핑 메시지 생성
    summary_msg = f"🌅 *[킹옥션 아침 브리핑]*\n\n"
    summary_msg += f"📅 *{date_str} ({weekday_kr})*\n\n"
    
    summary_msg += "📌 *오늘 확인해야 할 일*\n"
    summary_msg += "1. ERP 종합 현황판 확인 (신규 고객 및 데일리 지표)\n"
    summary_msg += "2. 어제 발송된 마케팅 콘텐츠 성과 체크\n"
    
    if weekday_kr == "월":
        summary_msg += "3. 주간 회의 준비 및 마케팅 전략 점검\n"
    elif weekday_kr == "금":
        summary_msg += "3. 주간 실적 마감 및 주말 캠페인 스케줄 확인\n"
        
    summary_msg += "\n📁 *오늘 꼭 봐야 할 파일*\n"
    summary_msg += "• [킹옥션 종합 ERP] - 가장 먼저 확인!\n"
    summary_msg += "• [킹옥션_CRM_시스템.html] - 밤사이 들어온 신규 문자/고객 확인\n"
    
    summary_msg += "\n오늘도 활기찬 하루 되시길 바랍니다! 🚀"

    # 1. 텔레그램 발송 (파일 첨부 없이 텍스트 브리핑만 발송)
    if bot_token and chat_id:
        if send_telegram_report(bot_token, chat_id, summary_msg):
            print(f"[{date_str}] 텔레그램 아침 브리핑 발송 성공")
        else:
            print(f"[{date_str}] 텔레그램 발송 실패")
            
    # 이메일 발송 로직은 아침 브리핑에서는 비활성화 하거나 간단하게 텍스트만 전달
    email_env = os.environ.get("EMAIL_CONFIG_JSON")
    email_config = json.loads(email_env) if email_env else config.get("email")
    
    if email_config:
        success = send_email_report(
            email_config['smtp_server'],
            email_config['smtp_port'],
            email_config['sender_email'],
            email_config['sender_password'],
            email_config['receiver_email'],
            f"[킹옥션] 아침 브리핑 ({date_str})",
            summary_msg.replace("*", ""), 
            None # 첨부파일 없음
        )
        if success:
            print("이메일 아침 브리핑 발송 완료!")
