# ⚽ 드론뷰 축구 전술 분석기

드론으로 촬영한 아마추어 축구 경기 영상을 AI로 분석하여 선수 감지, 진형 분석, 히트맵, 전술 추천을 제공하는 Windows 데스크톱 앱입니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| 선수 자동 감지 | YOLOv8 AI로 드론 영상에서 선수 위치 자동 추출 |
| 팀 자동 분리 | 유니폼 색상 분석으로 두 팀 자동 구분 |
| 진형 분석 | KMeans 클러스터링으로 4-4-2, 4-3-3 등 6가지 진형 감지 |
| 전술 추천 | 상대 진형에 따른 맞춤 한국어 전술 조언 |
| 히트맵 | 선수 활동 밀도 지도 시각화 |
| 이동 경로 | 팀별 선수 이동 패턴 시각화 |
| YouTube 분석 | URL 입력만으로 YouTube 영상 직접 분석 (다운로드 불필요) |
| 분석 중지 | 분석 도중 언제든 중지 가능 |

## 스크린샷

![메인 화면](https://github.com/davidk912/soccer_analyzer/assets/main-screenshot.png)

> 영상 업로드 또는 YouTube URL 입력 → 분석 실행 → 진형/히트맵/경로 3탭으로 결과 확인

## 설치 및 실행

### 방법 1: 실행 파일 (exe) 사용 — 권장

1. [Releases](https://github.com/davidk912/soccer_analyzer/releases/latest)에서 `soccer_analyzer_v1.1.0.zip` 다운로드
2. 압축 해제
3. `soccer_analyzer/soccer_analyzer.exe` 실행

> **주의**: 첫 실행 시 YOLOv8 모델(약 6MB)이 자동 다운로드됩니다. 인터넷 연결 필요.

### 방법 2: 소스코드 직접 실행

**요구사항**: Python 3.9 이상

```bash
# 1. 종속 패키지 설치
pip install -r requirements.txt

# 2. 실행
python src/main.py
```

## 사용법

1. **영상 열기** 버튼 클릭 → 드론 촬영 축구 영상 선택 (mp4, avi, mov)
   - 또는 **YouTube URL** 입력 후 **불러오기** 클릭
2. **샘플 간격** 설정 (기본 5 → 숫자 클수록 빠르고 정확도 낮아짐)
3. **분석 실행 ▶** 클릭 → AI 분석 시작
   - 분석 중 **■ 중지** 버튼으로 언제든 중단 가능
4. 분석 완료 후 3개 탭에서 결과 확인:
   - **진형 분석**: 팀 진형 + 전술 추천 텍스트 + 진형 다이어그램
   - **히트맵**: 팀 A / 팀 B / 전체 활동 밀도 지도
   - **이동 경로**: 경기 중 선수 이동 패턴

## 기술 스택

- **언어**: Python 3.x
- **UI**: PyQt5
- **AI 감지**: YOLOv8n (Ultralytics)
- **영상 처리**: OpenCV
- **분석**: scikit-learn (KMeans)
- **시각화**: Matplotlib, Seaborn
- **YouTube**: yt-dlp

## 프로젝트 구조

```
soccer_analyzer/
├── src/
│   ├── main.py         # PyQt5 메인 윈도우 + 워커 스레드
│   ├── analyzer.py     # YOLO 감지 + 진형 분석 + 전술 추천
│   └── visualizer.py   # 히트맵/경로 시각화 (matplotlib → QPixmap)
├── Release/
│   └── soccer_analyzer/   # exe + 의존 라이브러리
├── requirements.txt    # Python 종속 패키지 목록
├── build.bat           # exe 빌드 스크립트 (PyInstaller)
├── report.html         # 프로젝트 보고서
└── README.md
```

## exe 빌드 방법

```bash
pip install pyinstaller
build.bat
```

빌드 완료 후 `Release/soccer_analyzer/soccer_analyzer.exe` 생성됩니다.

## 지원 진형

4-4-2 · 4-3-3 · 3-5-2 · 4-2-3-1 · 5-3-2 · 4-1-4-1

## 버전 히스토리

| 버전 | 내용 |
|------|------|
| v1.1.0 | 실행 속도 개선 (onedir), 분석 중지 기능, YouTube 지원 |
| v1.0.0 | 최초 릴리즈 |

## 라이선스

MIT License
