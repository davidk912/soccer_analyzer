import cv2
import numpy as np
from sklearn.cluster import KMeans
from ultralytics import YOLO

# ─── 진형 템플릿 (정규화 좌표 [0,1], y=0이 위쪽) ───────────────────────────
FORMATION_TEMPLATES = {
    '4-4-2': [
        (0.15, 0.5),                                          # 골키퍼
        (0.30, 0.15), (0.30, 0.38), (0.30, 0.62), (0.30, 0.85),  # 수비 4
        (0.55, 0.15), (0.55, 0.38), (0.55, 0.62), (0.55, 0.85),  # 미드 4
        (0.78, 0.35), (0.78, 0.65),                           # 공격 2
    ],
    '4-3-3': [
        (0.15, 0.5),
        (0.30, 0.15), (0.30, 0.38), (0.30, 0.62), (0.30, 0.85),
        (0.55, 0.25), (0.55, 0.50), (0.55, 0.75),
        (0.78, 0.15), (0.78, 0.50), (0.78, 0.85),
    ],
    '3-5-2': [
        (0.15, 0.5),
        (0.30, 0.25), (0.30, 0.50), (0.30, 0.75),
        (0.52, 0.10), (0.52, 0.30), (0.52, 0.50), (0.52, 0.70), (0.52, 0.90),
        (0.78, 0.35), (0.78, 0.65),
    ],
    '4-2-3-1': [
        (0.15, 0.5),
        (0.28, 0.15), (0.28, 0.38), (0.28, 0.62), (0.28, 0.85),
        (0.48, 0.35), (0.48, 0.65),
        (0.65, 0.15), (0.65, 0.50), (0.65, 0.85),
        (0.82, 0.50),
    ],
    '5-3-2': [
        (0.15, 0.5),
        (0.28, 0.10), (0.28, 0.30), (0.28, 0.50), (0.28, 0.70), (0.28, 0.90),
        (0.55, 0.25), (0.55, 0.50), (0.55, 0.75),
        (0.78, 0.35), (0.78, 0.65),
    ],
    '4-1-4-1': [
        (0.15, 0.5),
        (0.28, 0.15), (0.28, 0.38), (0.28, 0.62), (0.28, 0.85),
        (0.43, 0.50),
        (0.60, 0.12), (0.60, 0.37), (0.60, 0.63), (0.60, 0.88),
        (0.82, 0.50),
    ],
}

# ─── 전술 추천 테이블 ────────────────────────────────────────────────────────
TACTICS_TABLE = {
    ('4-4-2', '4-3-3'): (
        "상대 3미드필더 대비 중앙 압박 강화가 필요합니다.\n"
        "• 양쪽 미드필더가 좁게 서서 중앙 패스 차단\n"
        "• 측면 공간 역습 시 2명의 스트라이커 빠른 전진\n"
        "• 세트피스 시 코너킥 니어포스트 공략 추천"
    ),
    ('4-4-2', '4-2-3-1'): (
        "상대 수비형 미드필더 2명을 고립시키는 전술이 효과적입니다.\n"
        "• 아래쪽 스트라이커가 수비형 미드필더 압박\n"
        "• 미드필더 측면이 상대 측면 공격수 견제\n"
        "• 롱볼로 상대 수비 라인 뒤 공간 공략"
    ),
    ('4-3-3', '4-4-2'): (
        "수적 열세인 중앙 미드필더를 보완하는 전술이 필요합니다.\n"
        "• 윙어가 수비 시 내려와 5미드필더 형태 유지\n"
        "• 측면 풀백 오버래핑 적극 활용\n"
        "• 원톱 스트라이커 전방 압박으로 상대 빌드업 차단"
    ),
    ('4-3-3', '3-5-2'): (
        "상대 5미드필더 대비 측면 공간이 핵심입니다.\n"
        "• 양 윙어 높게 배치, 상대 윙백 뒤 공간 공략\n"
        "• 풀백 공격 참여 자제, 역습 대비\n"
        "• 중앙 미드필더 3명이 삼각형 유지하며 볼 배급"
    ),
    ('3-5-2', '4-4-2'): (
        "중앙 미드필더 수적 우위를 최대한 활용하세요.\n"
        "• 미드필더 5명으로 상대 중앙 완전히 장악\n"
        "• 윙백이 측면 전체 커버, 공격과 수비 겸업\n"
        "• 투스트라이커 연계 플레이로 상대 수비 분산"
    ),
    ('4-2-3-1', '4-3-3'): (
        "수비 안정성을 기반으로 역습을 노리세요.\n"
        "• 수비형 미드필더 2명이 상대 3공격수 차단\n"
        "• 공격형 미드필더 3명이 빠른 전환 담당\n"
        "• 원톱이 공간 창출, 미드필더 침투 유도"
    ),
    ('5-3-2', '4-4-2'): (
        "수비적 안정성이 높으니 역습을 노리세요.\n"
        "• 수비 5명이 박스 수비 형성, 공간 최소화\n"
        "• 미드필더 3명 중 한명이 공격 시 앞으로\n"
        "• 2스트라이커 빠른 카운터어택 준비"
    ),
}

TACTICS_DEFAULT = (
    "현재 진형을 유지하며 안정적인 경기를 운영하세요.\n"
    "• 중앙 공간 밀집 수비로 상대 공격 차단\n"
    "• 측면 풀백을 통한 빌드업 활용\n"
    "• 세트피스 훈련을 통해 득점 기회 창출\n"
    "• 빠른 전방 압박으로 상대 빌드업 방해"
)


class SoccerAnalyzer:
    def __init__(self):
        self.model = YOLO('yolov8n.pt')
        self.frame_width = 0
        self.frame_height = 0

    def process_video(self, video_path, sample_every=5, progress_callback=None, stop_check=None):
        """영상에서 프레임을 샘플링하여 선수 감지 및 팀 분리 수행."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video_path}")

        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        team_a_positions = []  # [(x_norm, y_norm), ...]
        team_b_positions = []
        tracks = []  # [(frame_idx, x_px, y_px, team_id), ...]

        frame_idx = 0
        processed = 0

        while True:
            if stop_check and stop_check():
                break

            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_every == 0:
                detections = self._detect_players(frame)
                if len(detections) >= 2:
                    team_labels = self._assign_team_by_color(frame, detections)
                    for (x_c, y_c, bbox), team in zip(detections, team_labels):
                        x_norm = x_c / self.frame_width
                        y_norm = y_c / self.frame_height
                        if team == 0:
                            team_a_positions.append((x_norm, y_norm))
                        else:
                            team_b_positions.append((x_norm, y_norm))
                        tracks.append((frame_idx, x_c, y_c, team))

                processed += 1
                if progress_callback and total_frames > 0:
                    progress = int((frame_idx / total_frames) * 100)
                    progress_callback(progress)

            frame_idx += 1

        cap.release()

        return {
            'team_a_positions': team_a_positions,
            'team_b_positions': team_b_positions,
            'tracks': tracks,
            'frame_width': self.frame_width,
            'frame_height': self.frame_height,
        }

    def _detect_players(self, frame):
        """YOLOv8로 프레임에서 사람(선수) 감지."""
        results = self.model(frame, verbose=False)[0]
        detections = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id != 0 or conf < 0.4:  # class 0 = person
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            w, h = x2 - x1, y2 - y1

            # 너무 작거나 큰 박스 필터 (드론 뷰에서 선수 크기 범위)
            if w < 10 or h < 10 or w > 300 or h > 300:
                continue

            x_c = (x1 + x2) // 2
            y_c = (y1 + y2) // 2
            detections.append((x_c, y_c, (x1, y1, x2, y2)))

        return detections

    def _assign_team_by_color(self, frame, detections):
        """유니폼 색상(HSV 색조)으로 팀 분리."""
        hues = []
        for (x_c, y_c, (x1, y1, x2, y2)) in detections:
            # 상단 2/3 크롭 (유니폼 영역)
            jersey_y2 = y1 + (y2 - y1) * 2 // 3
            crop = frame[y1:jersey_y2, x1:x2]

            if crop.size == 0:
                hues.append(0.0)
                continue

            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            mean_hue = float(np.mean(hsv[:, :, 0]))
            hues.append(mean_hue)

        if len(hues) < 2:
            return [0] * len(detections)

        hues_arr = np.array(hues).reshape(-1, 1)

        try:
            km = KMeans(n_clusters=2, n_init=10, random_state=42)
            labels = km.fit_predict(hues_arr)

            # 팀 분리 검증: 두 팀이 각각 최소 2명 이상
            if labels.tolist().count(0) < 2 or labels.tolist().count(1) < 2:
                raise ValueError("팀 분리 실패")

            return labels.tolist()

        except Exception:
            # Fallback: x좌표 기준으로 좌/우 분리
            mid_x = self.frame_width / 2
            return [0 if x_c < mid_x else 1 for (x_c, y_c, _) in detections]

    def analyze_formation(self, positions):
        """선수 위치 리스트로 진형 분석. 최근접 템플릿 매칭."""
        if len(positions) < 4:
            return 'Unknown', []

        pos_arr = np.array(positions)

        # 선수 수에 맞게 클러스터 수 결정 (골키퍼 포함 최대 11명 고려)
        n_clusters = min(5, max(3, len(positions) // 2))

        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        km.fit(pos_arr)
        centers = km.cluster_centers_

        # 각 진형 템플릿과 거리 계산
        best_formation = 'Unknown'
        best_dist = float('inf')

        for name, template in FORMATION_TEMPLATES.items():
            tmpl_arr = np.array(template)
            # 템플릿을 n_clusters 그룹으로 분할하여 비교
            tmpl_km = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
            tmpl_km.fit(tmpl_arr)
            tmpl_centers = tmpl_km.cluster_centers_

            # 정렬 후 거리 계산 (y좌표 기준)
            c_sorted = centers[np.argsort(centers[:, 0])]
            t_sorted = tmpl_centers[np.argsort(tmpl_centers[:, 0])]
            dist = float(np.sum(np.linalg.norm(c_sorted - t_sorted, axis=1)))

            if dist < best_dist:
                best_dist = dist
                best_formation = name

        return best_formation, centers.tolist()

    def get_tactical_recommendation(self, team_a_formation, team_b_formation):
        """두 팀 진형 기반 전술 추천 반환."""
        key = (team_a_formation, team_b_formation)
        return TACTICS_TABLE.get(key, TACTICS_DEFAULT)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("사용법: python analyzer.py <video_path>")
        sys.exit(1)

    analyzer = SoccerAnalyzer()
    print("영상 분석 중...")
    results = analyzer.process_video(sys.argv[1], sample_every=10,
                                     progress_callback=lambda p: print(f"\r진행: {p}%", end=''))
    print()

    team_a_formation, _ = analyzer.analyze_formation(results['team_a_positions'])
    team_b_formation, _ = analyzer.analyze_formation(results['team_b_positions'])
    recommendation = analyzer.get_tactical_recommendation(team_a_formation, team_b_formation)

    print(f"팀 A 진형: {team_a_formation}")
    print(f"팀 B 진형: {team_b_formation}")
    print(f"\n전술 추천:\n{recommendation}")
