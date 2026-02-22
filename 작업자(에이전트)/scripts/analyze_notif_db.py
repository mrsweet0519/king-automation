import sqlite3
import os
import glob

# Your Phone DB 경로 찾기
base_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.YourPhone_8wekyb3d8bbwe\LocalCache\Indexed")
db_files = glob.glob(os.path.join(base_path, "**/notifications.db"), recursive=True)

if not db_files:
    print("notifications.db를 찾을 수 없습니다.")
    exit()

db_path = db_files[0]
print(f"DB 분석 시작: {db_path}")

try:
    # DB 파일을 임시로 복사 (사용 중일 수 있으므로)
    temp_db = "temp_notif.db"
    import shutil
    shutil.copy2(db_path, temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # 테이블 목록 확인
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"테이블 목록: {tables}")
    
    for table in tables:
        table_name = table[0]
        print(f"\n--- {table_name} ---")
        cursor.execute(f"PRAGMA table_info({table_name});")
        print("컬럼 정보:", cursor.fetchall())
        
        # 최근 데이터 샘플
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        print("데이터 샘플:", cursor.fetchall())
        
    conn.close()
    os.remove(temp_db)
except Exception as e:
    print(f"분석 중 오류 발생: {e}")
