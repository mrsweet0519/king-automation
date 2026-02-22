@echo off
taskkill /F /IM python.exe /T >nul 2>&1
echo 킹옥션 다이렉트 동기화 서버 가동 중...
pushd "%~dp0"
python crm_direct_sync.py
popd
pause
