import io
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUI 없는 백엔드 (Qt 충돌 방지)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Arc, FancyArrow
import cv2
from PyQt5.QtGui import QPixmap, QImage


TEAM_A_COLOR = '#1565C0'   # 파란색
TEAM_B_COLOR = '#C62828'   # 빨간색


def draw_field_background(ax, flip=False):
    """matplotlib Axes에 축구 필드 배경 그리기 (정규화 좌표 기준)."""
    # 필드 배경
    field = mpatches.FancyBboxPatch((0, 0), 1, 1,
                                     boxstyle="square,pad=0",
                                     facecolor='#2d5a1b', edgecolor='white', linewidth=2)
    ax.add_patch(field)

    # 센터라인
    ax.axvline(x=0.5, color='white', linewidth=1.5, alpha=0.8)

    # 센터 서클
    center_circle = Circle((0.5, 0.5), 0.1, fill=False, color='white', linewidth=1.5)
    ax.add_patch(center_circle)
    ax.plot(0.5, 0.5, 'wo', markersize=4)

    # 페널티 박스 (왼쪽)
    left_box = mpatches.Rectangle((0, 0.21), 0.165, 0.58,
                                   fill=False, edgecolor='white', linewidth=1.5)
    ax.add_patch(left_box)

    # 페널티 박스 (오른쪽)
    right_box = mpatches.Rectangle((0.835, 0.21), 0.165, 0.58,
                                    fill=False, edgecolor='white', linewidth=1.5)
    ax.add_patch(right_box)

    # 골박스 (왼쪽)
    left_goal = mpatches.Rectangle((0, 0.35), 0.055, 0.30,
                                    fill=False, edgecolor='white', linewidth=1.5)
    ax.add_patch(left_goal)

    # 골박스 (오른쪽)
    right_goal = mpatches.Rectangle((0.945, 0.35), 0.055, 0.30,
                                     fill=False, edgecolor='white', linewidth=1.5)
    ax.add_patch(right_goal)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.axis('off')


def fig_to_pixmap(fig):
    """matplotlib Figure를 QPixmap으로 변환."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=80, bbox_inches='tight',
                facecolor='#1a1a2e')
    buf.seek(0)
    pixmap = QPixmap()
    pixmap.loadFromData(buf.read())
    buf.close()
    plt.close(fig)
    return pixmap


def generate_heatmap(positions, title="히트맵", color=TEAM_A_COLOR):
    """선수 위치 히트맵 생성 → QPixmap 반환."""
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('#1a1a2e')

    draw_field_background(ax)

    if len(positions) > 3:
        pos_arr = np.array(positions)
        xs, ys = pos_arr[:, 0], pos_arr[:, 1]

        try:
            ax.hexbin(xs, ys, gridsize=12, cmap='YlOrRd', alpha=0.6,
                      extent=[0, 1, 0, 1], mincnt=1)
        except Exception:
            ax.scatter(xs, ys, c=color, alpha=0.5, s=20)
    else:
        ax.text(0.5, 0.5, '데이터 부족', ha='center', va='center',
                color='white', fontsize=12, transform=ax.transAxes)

    ax.set_title(title, color='white', fontsize=11, pad=6)
    return fig_to_pixmap(fig)


def generate_formation_diagram(team_a_positions, team_b_positions,
                                team_a_formation='', team_b_formation=''):
    """두 팀 진형을 필드 위에 점으로 표시 → QPixmap 반환."""
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('#1a1a2e')

    draw_field_background(ax)

    # 팀 A 선수 (왼쪽 절반)
    if team_a_positions:
        pos_arr = np.array(team_a_positions)
        # 왼쪽 절반으로 스케일
        xs = pos_arr[:, 0] * 0.48
        ys = pos_arr[:, 1]
        ax.scatter(xs, ys, c=TEAM_A_COLOR, s=80, zorder=5, edgecolors='white',
                   linewidths=0.8, label=f'팀 A ({team_a_formation})')

    # 팀 B 선수 (오른쪽 절반, 방향 반전)
    if team_b_positions:
        pos_arr = np.array(team_b_positions)
        xs = 1 - pos_arr[:, 0] * 0.48
        ys = pos_arr[:, 1]
        ax.scatter(xs, ys, c=TEAM_B_COLOR, s=80, zorder=5, edgecolors='white',
                   linewidths=0.8, label=f'팀 B ({team_b_formation})')

    legend = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02),
                       ncol=2, framealpha=0.3, labelcolor='white',
                       fontsize=9)
    legend.get_frame().set_facecolor('#1a1a2e')

    ax.set_title('진형 분석', color='white', fontsize=11, pad=6)
    return fig_to_pixmap(fig)


def generate_path_overlay(tracks, frame_width, frame_height,
                           show_team_a=True, show_team_b=True):
    """선수 이동 경로를 필드 위에 표시 → QPixmap 반환."""
    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor('#1a1a2e')

    draw_field_background(ax)

    if tracks:
        # 팀별로 분리
        team_a = [(x / frame_width, y / frame_height)
                  for (_, x, y, t) in tracks if t == 0]
        team_b = [(x / frame_width, y / frame_height)
                  for (_, x, y, t) in tracks if t == 1]

        if show_team_a and len(team_a) > 1:
            xs, ys = zip(*team_a)
            ax.plot(xs, ys, '-', color=TEAM_A_COLOR, alpha=0.5, linewidth=0.8)
            ax.scatter(xs[::max(1, len(xs)//20)], ys[::max(1, len(ys)//20)],
                       c=TEAM_A_COLOR, s=15, zorder=5, alpha=0.8)

        if show_team_b and len(team_b) > 1:
            xs, ys = zip(*team_b)
            ax.plot(xs, ys, '-', color=TEAM_B_COLOR, alpha=0.5, linewidth=0.8)
            ax.scatter(xs[::max(1, len(xs)//20)], ys[::max(1, len(ys)//20)],
                       c=TEAM_B_COLOR, s=15, zorder=5, alpha=0.8)

    ax.set_title('이동 경로', color='white', fontsize=11, pad=6)
    return fig_to_pixmap(fig)


def numpy_frame_to_pixmap(frame):
    """OpenCV BGR 프레임(numpy) → QPixmap 변환."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
    return QPixmap.fromImage(qt_image)


if __name__ == '__main__':
    # 테스트: 랜덤 위치로 각 시각화 확인
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    fake_a = [(np.random.uniform(0.1, 0.5), np.random.uniform(0.1, 0.9))
               for _ in range(50)]
    fake_b = [(np.random.uniform(0.5, 0.9), np.random.uniform(0.1, 0.9))
               for _ in range(50)]
    fake_tracks = [(i, int(x * 640), int(y * 480), t)
                    for i, ((x, y), t) in enumerate(
                        [(p, 0) for p in fake_a] + [(p, 1) for p in fake_b])]

    pm1 = generate_heatmap(fake_a, "팀 A 히트맵")
    pm1.save('test_heatmap.png')
    print("test_heatmap.png 저장됨")

    pm2 = generate_formation_diagram(fake_a, fake_b, '4-4-2', '4-3-3')
    pm2.save('test_formation.png')
    print("test_formation.png 저장됨")

    pm3 = generate_path_overlay(fake_tracks, 640, 480)
    pm3.save('test_paths.png')
    print("test_paths.png 저장됨")
