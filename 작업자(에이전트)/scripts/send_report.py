import os
import requests
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# 킹옥션 정이사 보고서 발송 시스템 (Telegram & Email Version)

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
    CONFIG_PATH = os.environ.get("DELIVERY_CONFIG_PATH", "delivery_config.json")
    
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
    # 환경 변수 우선 적용
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("bot_token")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("chat_id")
    dashboard_path = os.environ.get("DASHBOARD_PATH") or config.get("dashboard_path")
    
    today = datetime.now().strftime("%Y-%m-%d")
    summary_msg = f"🚩 *[킹옥션 보고]* {today}\n\n오늘의 마케팅 통합 대시보드가 업데이트되었습니다.\n첨부된 HTML 파일을 확인해 주세요."

    # 1. 텔레그램 발송
    if bot_token and chat_id:
        if send_telegram_report(bot_token, chat_id, summary_msg, dashboard_path):
            print("텔레그램 보고서 발송 완료!")
        else:
            # 파일이 없더라도 텍스트 보고는 시도
            send_telegram_report(bot_token, chat_id, f"{summary_msg}\n\n(참고: 대시보드 파일이 클라우드 경로에 없어 요약만 발송되었습니다.)")

    # 2. 이메일 발송
    # GitHub Actions 환경 변수로부터 이메일 설정 로드 (복잡하므로 JSON 문자열로 받을 수도 있음)
    email_env = os.environ.get("EMAIL_CONFIG_JSON")
    email_config = json.loads(email_env) if email_env else config.get("email")
    
    if email_config:
        success = send_email_report(
            email_config['smtp_server'],
            email_config['smtp_port'],
            email_config['sender_email'],
            email_config['sender_password'],
            email_config['receiver_email'],
            f"[킹옥션] 마케팅 분석 보고서 ({today})",
            summary_msg.replace("*", ""), 
            dashboard_path
        )
        if success:
            print("이메일 보고서 발송 완료!")
