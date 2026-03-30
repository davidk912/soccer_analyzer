@echo off
echo ======================================
echo  드론뷰 축구 전술 분석기 - exe 빌드
echo ======================================

:: PyInstaller 설치 확인
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 설치 중...
    pip install pyinstaller
)

:: Release 폴더 생성
if not exist "Release" mkdir Release

:: 빌드 실행
echo.
echo 빌드 중... (수 분 소요될 수 있습니다)
pyinstaller ^
    --onefile ^
    --windowed ^
    --name soccer_analyzer ^
    --distpath Release ^
    --workpath build_tmp ^
    --specpath build_tmp ^
    --add-data "src;src" ^
    src/main.py

:: 임시 파일 정리
if exist "build_tmp" rmdir /s /q build_tmp

echo.
if exist "Release\soccer_analyzer.exe" (
    echo [성공] Release\soccer_analyzer.exe 생성 완료!
) else (
    echo [실패] 빌드에 실패했습니다. 오류 메시지를 확인하세요.
)
pause
