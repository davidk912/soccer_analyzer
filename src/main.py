import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QProgressBar, QFileDialog, QTabWidget,
    QTextEdit, QSpinBox, QCheckBox, QSizePolicy, QFrame, QMessageBox,
    QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QPalette, QColor
import cv2

from analyzer import SoccerAnalyzer
import visualizer


# ─── 스타일 상수 ─────────────────────────────────────────────────────────────
DARK_BG = '#0d1117'
CARD_BG = '#161b22'
BORDER = '#30363d'
ACCENT = '#1f6feb'
TEXT = '#e6edf3'
SUBTEXT = '#8b949e'
TEAM_A = '#1565C0'
TEAM_B = '#C62828'

STYLE = f"""
QMainWindow, QWidget {{
    background-color: {DARK_BG};
    color: {TEXT};
    font-family: 'Segoe UI', sans-serif;
}}
QPushButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton:hover {{ background-color: #388bfd; }}
QPushButton:disabled {{ background-color: #21262d; color: {SUBTEXT}; }}
QPushButton#open_btn {{ background-color: #21262d; border: 1px solid {BORDER}; }}
QPushButton#open_btn:hover {{ background-color: #30363d; }}
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: #21262d;
    height: 20px;
    text-align: center;
    color: white;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background-color: {CARD_BG};
    border-radius: 6px;
}}
QTabBar::tab {{
    background-color: #21262d;
    color: {SUBTEXT};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {CARD_BG};
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QTextEdit {{
    background-color: #0d1117;
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    font-size: 13px;
    padding: 8px;
    line-height: 1.6;
}}
QLabel#video_label {{
    background-color: #0a0e14;
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLabel#formation_badge {{
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 14px;
    font-weight: bold;
}}
QSpinBox {{
    background-color: #21262d;
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 4px 8px;
}}
QCheckBox {{ color: {TEXT}; font-size: 13px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
"""


# ─── YouTube URL 추출 워커 ───────────────────────────────────────────────────
class YoutubeWorker(QThread):
    finished = pyqtSignal(str, str)  # (stream_url, title)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                stream_url = info['url']
                title = info.get('title', 'YouTube 영상')
            self.finished.emit(stream_url, title)
        except ImportError:
            self.error.emit("yt-dlp가 설치되지 않았습니다.\n터미널에서 실행: pip install yt-dlp")
        except Exception as e:
            self.error.emit(f"YouTube URL 로드 실패:\n{str(e)}")


# ─── 분석 워커 스레드 ────────────────────────────────────────────────────────
class AnalysisWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, video_path, sample_every):
        super().__init__()
        self.video_path = video_path
        self.sample_every = sample_every
        self.analyzer = SoccerAnalyzer()

    def run(self):
        try:
            raw = self.analyzer.process_video(
                self.video_path,
                sample_every=self.sample_every,
                progress_callback=lambda p: self.progress.emit(p)
            )
            self.progress.emit(90)

            team_a_formation, team_a_centers = self.analyzer.analyze_formation(
                raw['team_a_positions'])
            team_b_formation, team_b_centers = self.analyzer.analyze_formation(
                raw['team_b_positions'])
            recommendation = self.analyzer.get_tactical_recommendation(
                team_a_formation, team_b_formation)

            self.progress.emit(100)
            self.finished.emit({
                'team_a_positions': raw['team_a_positions'],
                'team_b_positions': raw['team_b_positions'],
                'team_a_formation': team_a_formation,
                'team_b_formation': team_b_formation,
                'team_a_centers': team_a_centers,
                'team_b_centers': team_b_centers,
                'recommendation': recommendation,
                'tracks': raw['tracks'],
                'frame_width': raw['frame_width'],
                'frame_height': raw['frame_height'],
            })
        except Exception as e:
            self.error.emit(str(e))


# ─── 메인 윈도우 ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_path = None
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.worker = None
        self.analysis_results = None

        self.setWindowTitle('드론뷰 축구 전술 분석기')
        self.setFixedSize(1200, 680)
        self.setStyleSheet(STYLE)

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 10, 12, 10)

        # 상단 툴바
        toolbar = self._create_toolbar()
        root.addLayout(toolbar)

        # YouTube URL 입력 행
        root.addLayout(self._create_youtube_row())

        # 메인 컨텐츠 (좌 비디오 + 우 분석)
        content = QHBoxLayout()
        content.setSpacing(12)
        content.addWidget(self._create_video_panel(), 6)
        content.addWidget(self._create_analysis_panel(), 5)
        root.addLayout(content)

    def _create_toolbar(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # 타이틀
        title = QLabel('⚽ 드론뷰 축구 전술 분석기')
        title.setStyleSheet(f'font-size: 16px; font-weight: bold; color: {TEXT};')
        layout.addWidget(title)
        layout.addStretch()

        # 영상 열기
        self.open_btn = QPushButton('영상 열기')
        self.open_btn.setObjectName('open_btn')
        self.open_btn.clicked.connect(self.open_video)
        layout.addWidget(self.open_btn)

        # 샘플 간격
        sample_label = QLabel('샘플 간격:')
        sample_label.setStyleSheet(f'color: {SUBTEXT}; font-size: 12px;')
        layout.addWidget(sample_label)
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(1, 30)
        self.sample_spin.setValue(5)
        self.sample_spin.setToolTip('N프레임마다 1개 분석 (클수록 빠름)')
        layout.addWidget(self.sample_spin)

        # 분석 실행
        self.analyze_btn = QPushButton('분석 실행 ▶')
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.run_analysis)
        layout.addWidget(self.analyze_btn)

        # 진행바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(160)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 재생/정지
        self.play_btn = QPushButton('▶ 재생')
        self.play_btn.setObjectName('open_btn')
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_btn)

        return layout

    def _create_youtube_row(self):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        yt_icon = QLabel('▶ YouTube URL:')
        yt_icon.setStyleSheet(f'color: #ff4444; font-size: 12px; font-weight: bold;')
        layout.addWidget(yt_icon)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('https://www.youtube.com/watch?v=...')
        self.url_input.setStyleSheet(
            f'background-color: #21262d; border: 1px solid {BORDER}; '
            f'border-radius: 6px; color: {TEXT}; padding: 6px 10px; font-size: 13px;'
        )
        self.url_input.returnPressed.connect(self.load_youtube_url)
        layout.addWidget(self.url_input)

        self.yt_btn = QPushButton('불러오기')
        self.yt_btn.setObjectName('open_btn')
        self.yt_btn.clicked.connect(self.load_youtube_url)
        layout.addWidget(self.yt_btn)

        self.yt_status = QLabel('')
        self.yt_status.setStyleSheet(f'color: {SUBTEXT}; font-size: 11px;')
        layout.addWidget(self.yt_status)

        return layout

    def _create_video_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f'background-color: {CARD_BG}; border-radius: 8px;')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        self.video_label = QLabel()
        self.video_label.setObjectName('video_label')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setText('영상을 열어주세요')
        self.video_label.setStyleSheet(
            f'color: {SUBTEXT}; font-size: 14px; '
            f'background-color: #0a0e14; border: 1px solid {BORDER}; border-radius: 8px;'
        )
        layout.addWidget(self.video_label)

        # 파일명 표시
        self.file_label = QLabel('파일 없음')
        self.file_label.setStyleSheet(f'color: {SUBTEXT}; font-size: 11px;')
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)

        return panel

    def _create_analysis_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f'background-color: {CARD_BG}; border-radius: 8px;')
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self._create_formation_tab(), '진형 분석')
        self.tabs.addTab(self._create_heatmap_tab(), '히트맵')
        self.tabs.addTab(self._create_path_tab(), '이동 경로')

        return panel

    def _create_formation_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        # 팀 진형 표시
        badges = QHBoxLayout()
        self.team_a_badge = QLabel('팀 A: -')
        self.team_a_badge.setObjectName('formation_badge')
        self.team_a_badge.setStyleSheet(
            f'background-color: {TEAM_A}22; color: #90caf9; '
            f'border: 1px solid {TEAM_A}; border-radius: 6px; '
            f'padding: 6px 12px; font-size: 14px; font-weight: bold;'
        )
        self.team_b_badge = QLabel('팀 B: -')
        self.team_b_badge.setObjectName('formation_badge')
        self.team_b_badge.setStyleSheet(
            f'background-color: {TEAM_B}22; color: #ef9a9a; '
            f'border: 1px solid {TEAM_B}; border-radius: 6px; '
            f'padding: 6px 12px; font-size: 14px; font-weight: bold;'
        )
        badges.addWidget(self.team_a_badge)
        badges.addStretch()
        badges.addWidget(self.team_b_badge)
        layout.addLayout(badges)

        # 전술 추천 텍스트
        tactics_title = QLabel('전술 추천')
        tactics_title.setStyleSheet(f'color: {SUBTEXT}; font-size: 11px; font-weight: bold;')
        layout.addWidget(tactics_title)

        self.tactics_text = QTextEdit()
        self.tactics_text.setReadOnly(True)
        self.tactics_text.setPlaceholderText('분석 후 전술 추천이 표시됩니다...')
        self.tactics_text.setMaximumHeight(100)
        layout.addWidget(self.tactics_text)

        # 진형 다이어그램
        self.formation_img = QLabel()
        self.formation_img.setAlignment(Qt.AlignCenter)
        self.formation_img.setStyleSheet(f'background-color: #0d1117; border-radius: 6px;')
        self.formation_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.formation_img)

        return tab

    def _create_heatmap_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        # 팀 선택 버튼
        btn_layout = QHBoxLayout()
        self.hm_team_a_btn = QPushButton('팀 A')
        self.hm_team_b_btn = QPushButton('팀 B')
        self.hm_combined_btn = QPushButton('전체')
        for btn in [self.hm_team_a_btn, self.hm_team_b_btn, self.hm_combined_btn]:
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                f'background-color: #21262d; color: {TEXT}; border: 1px solid {BORDER};'
                f'border-radius: 4px; font-size: 12px; padding: 4px 12px;'
            )
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self.hm_team_a_btn.clicked.connect(lambda: self.update_heatmap('a'))
        self.hm_team_b_btn.clicked.connect(lambda: self.update_heatmap('b'))
        self.hm_combined_btn.clicked.connect(lambda: self.update_heatmap('all'))

        # 히트맵 이미지
        self.heatmap_img = QLabel()
        self.heatmap_img.setAlignment(Qt.AlignCenter)
        self.heatmap_img.setStyleSheet(f'background-color: #0d1117; border-radius: 6px;')
        self.heatmap_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.heatmap_img)

        return tab

    def _create_path_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        options = QHBoxLayout()
        self.show_a_check = QCheckBox('팀 A 경로')
        self.show_a_check.setChecked(True)
        self.show_b_check = QCheckBox('팀 B 경로')
        self.show_b_check.setChecked(True)
        self.show_a_check.stateChanged.connect(self.update_paths)
        self.show_b_check.stateChanged.connect(self.update_paths)
        options.addWidget(self.show_a_check)
        options.addWidget(self.show_b_check)
        options.addStretch()
        layout.addLayout(options)

        self.path_img = QLabel()
        self.path_img.setAlignment(Qt.AlignCenter)
        self.path_img.setStyleSheet(f'background-color: #0d1117; border-radius: 6px;')
        self.path_img.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.path_img)

        return tab

    # ─── 슬롯 ────────────────────────────────────────────────────────────────
    def load_youtube_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if 'youtube.com' not in url and 'youtu.be' not in url:
            QMessageBox.warning(self, '잘못된 URL', 'YouTube URL을 입력해주세요.')
            return

        self.yt_btn.setEnabled(False)
        self.yt_status.setText('URL 처리 중...')
        self.yt_status.setStyleSheet(f'color: {SUBTEXT}; font-size: 11px;')

        self.yt_worker = YoutubeWorker(url)
        self.yt_worker.finished.connect(self._on_youtube_loaded)
        self.yt_worker.error.connect(self._on_youtube_error)
        self.yt_worker.start()

    def _on_youtube_loaded(self, stream_url, title):
        self.yt_btn.setEnabled(True)
        self.yt_status.setText(f'로드됨: {title[:30]}...' if len(title) > 30 else f'로드됨: {title}')
        self.yt_status.setStyleSheet('color: #56d364; font-size: 11px;')

        self.video_path = stream_url
        self.file_label.setText(f'[YouTube] {title}')
        self.analyze_btn.setEnabled(True)
        self.play_btn.setEnabled(True)

        # 첫 프레임 미리보기
        cap = cv2.VideoCapture(stream_url)
        ret, frame = cap.read()
        cap.release()
        if ret:
            pm = visualizer.numpy_frame_to_pixmap(frame)
            self.video_label.setPixmap(
                pm.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(stream_url)

    def _on_youtube_error(self, msg):
        self.yt_btn.setEnabled(True)
        self.yt_status.setText('로드 실패')
        self.yt_status.setStyleSheet('color: #f85149; font-size: 11px;')
        QMessageBox.critical(self, 'YouTube 로드 오류', msg)

    def open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, '영상 파일 선택', '',
            '영상 파일 (*.mp4 *.avi *.mov *.mkv *.MP4 *.AVI);;모든 파일 (*)'
        )
        if not path:
            return

        self.video_path = path
        self.file_label.setText(os.path.basename(path))
        self.analyze_btn.setEnabled(True)
        self.play_btn.setEnabled(True)

        # 첫 프레임 미리보기
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            pm = visualizer.numpy_frame_to_pixmap(frame)
            self.video_label.setPixmap(
                pm.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        # 재생용 캡처 초기화
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(path)

    def run_analysis(self):
        if not self.video_path:
            return

        self.analyze_btn.setEnabled(False)
        self.open_btn.setEnabled(False)
        self.yt_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.tactics_text.setPlainText('분석 중...')

        self.worker = AnalysisWorker(self.video_path, self.sample_spin.value())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_analysis_complete)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

    def on_analysis_complete(self, results):
        self.analysis_results = results
        self.analyze_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.yt_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # 진형 탭 업데이트
        self.team_a_badge.setText(f"팀 A: {results['team_a_formation']}")
        self.team_b_badge.setText(f"팀 B: {results['team_b_formation']}")
        self.tactics_text.setPlainText(results['recommendation'])

        # 진형 다이어그램
        pm = visualizer.generate_formation_diagram(
            results['team_a_positions'],
            results['team_b_positions'],
            results['team_a_formation'],
            results['team_b_formation'],
        )
        self._set_pixmap(self.formation_img, pm)

        # 히트맵 (기본: 팀 A)
        self.update_heatmap('a')

        # 경로
        self.update_paths()

        # 완료 알림
        QMessageBox.information(
            self, '분석 완료',
            f"분석이 완료되었습니다!\n\n"
            f"팀 A 진형: {results['team_a_formation']}\n"
            f"팀 B 진형: {results['team_b_formation']}"
        )

    def on_analysis_error(self, msg):
        self.analyze_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.yt_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, '분석 오류', f'분석 중 오류가 발생했습니다:\n{msg}')

    def update_heatmap(self, team):
        if not self.analysis_results:
            return
        r = self.analysis_results
        if team == 'a':
            pm = visualizer.generate_heatmap(r['team_a_positions'],
                                              f"팀 A 히트맵 ({r['team_a_formation']})",
                                              visualizer.TEAM_A_COLOR)
        elif team == 'b':
            pm = visualizer.generate_heatmap(r['team_b_positions'],
                                              f"팀 B 히트맵 ({r['team_b_formation']})",
                                              visualizer.TEAM_B_COLOR)
        else:
            combined = r['team_a_positions'] + r['team_b_positions']
            pm = visualizer.generate_heatmap(combined, '전체 히트맵')
        self._set_pixmap(self.heatmap_img, pm)

    def update_paths(self):
        if not self.analysis_results:
            return
        r = self.analysis_results
        pm = visualizer.generate_path_overlay(
            r['tracks'], r['frame_width'], r['frame_height'],
            show_team_a=self.show_a_check.isChecked(),
            show_team_b=self.show_b_check.isChecked(),
        )
        self._set_pixmap(self.path_img, pm)

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.play_btn.setText('▶ 재생')
        else:
            self.timer.start(33)  # ~30fps
            self.play_btn.setText('⏸ 정지')

    def update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        pm = visualizer.numpy_frame_to_pixmap(frame)
        self.video_label.setPixmap(
            pm.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _set_pixmap(self, label, pixmap):
        """QLabel 크기에 맞게 pixmap 스케일링."""
        label.setPixmap(
            pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
        event.accept()


# ─── 진입점 ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 다크 팔레트
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(13, 17, 23))
    palette.setColor(QPalette.WindowText, QColor(230, 237, 243))
    palette.setColor(QPalette.Base, QColor(22, 27, 34))
    palette.setColor(QPalette.AlternateBase, QColor(13, 17, 23))
    palette.setColor(QPalette.Text, QColor(230, 237, 243))
    palette.setColor(QPalette.Button, QColor(33, 38, 45))
    palette.setColor(QPalette.ButtonText, QColor(230, 237, 243))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
