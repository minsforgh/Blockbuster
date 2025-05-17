"""
블록 배치 시각화 도구 모듈
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import to_rgba
import random


class Visualizer:
    """
    블록 배치 시각화 도구 클래스

    Attributes:
        block_colors (dict): 블록 ID별 색상 매핑
    """

    def __init__(self):
        """Visualizer 초기화"""
        self.block_colors = {}

    def _get_block_color(self, block_id):
        """
        블록 ID에 대한 색상 반환 (일관성 유지)

        Args:
            block_id (str): 블록 ID

        Returns:
            tuple: RGBA 색상 값
        """
        if block_id not in self.block_colors:
            # 랜덤 색상 생성 (파스텔 톤)
            r = random.uniform(0.4, 0.8)
            g = random.uniform(0.4, 0.8)
            b = random.uniform(0.4, 0.8)
            self.block_colors[block_id] = (r, g, b, 0.8)

        return self.block_colors[block_id]

    def visualize_2d(self, placement_area, title="2D Block Placement", show=True, save_path=None):
        """
        2D 배치도 시각화

        Args:
            placement_area (PlacementArea): 배치 영역
            title (str): 그래프 제목
            show (bool): 그래프 표시 여부
            save_path (str): 저장 경로 (None인 경우 저장하지 않음)

        Returns:
            matplotlib.figure.Figure: 생성된 그림 객체
        """
        fig, ax = plt.subplots(figsize=(10, 10))

        # 배치 영역 경계 설정
        ax.set_xlim(0, placement_area.width)
        ax.set_ylim(0, placement_area.height)

        # 그리드 표시
        ax.grid(True, linestyle='--', alpha=0.7)

        # 정사각형 셀을 위한 동일한 축 비율 설정
        ax.set_aspect('equal')

        # 배치된 블록 표시
        for block_id, block in placement_area.placed_blocks.items():
            color = self._get_block_color(block_id)

            # 블록의 바닥 면적 계산
            footprint = block.get_positioned_footprint()

            # 각 복셀 표시
            for x, y in footprint:
                rect = patches.Rectangle(
                    (x, y), 1, 1,
                    linewidth=1,
                    edgecolor='black',
                    facecolor=color,
                    alpha=0.8
                )
                ax.add_patch(rect)

                # 블록 ID 표시 (첫 번째 복셀에만)
                if (x, y) == next(iter(footprint)):
                    ax.text(
                        x + 0.5, y + 0.5,
                        block_id,
                        ha='center', va='center',
                        fontsize=8, fontweight='bold'
                    )

        # 축 레이블 설정
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title(title)

        # 배치 정보 표시
        info_text = f"Placed: {len(placement_area.placed_blocks)}, " \
                   f"Unplaced: {len(placement_area.unplaced_blocks)}, " \
                   f"Score: {placement_area.get_placement_score():.4f}"
        ax.text(
            0.5, -0.05,
            info_text,
            ha='center', va='center',
            transform=ax.transAxes,
            fontsize=10
        )

        plt.tight_layout()

        # 그림 저장
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        # 그림 표시
        if show:
            plt.show()
        else:
            plt.close()

        return fig

    def visualize_3d(self, placement_area, title="3D Block Placement", show=True, save_path=None):
        """
        3D 배치 결과 시각화

        Args:
            placement_area (PlacementArea): 배치 영역
            title (str): 그래프 제목
            show (bool): 그래프 표시 여부
            save_path (str): 저장 경로 (None인 경우 저장하지 않음)

        Returns:
            matplotlib.figure.Figure: 생성된 그림 객체
        """
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        # 배치된 블록 표시
        for block_id, block in placement_area.placed_blocks.items():
            color = self._get_block_color(block_id)

            # 블록의 복셀 데이터 계산
            voxels = block.get_positioned_voxels()

            # 각 복셀 표시
            for x, y, heights in voxels:
                empty_below, filled, empty_above = heights

                # 채워진 공간 표시
                for z in range(empty_below, empty_below + filled):
                    # 복셀 표시
                    ax.bar3d(
                        x, y, z,
                        1, 1, 1,
                        color=color,
                        alpha=0.8,
                        shade=True
                    )

        # 축 레이블 설정
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(title)

        # 축 범위 설정
        ax.set_xlim(0, placement_area.width)
        ax.set_ylim(0, placement_area.height)
        ax.set_zlim(0, 10)  # Z축 범위는 적절히 조정

        # 3D 그래프에서 정사각형 셀을 위한 설정
        ax.set_box_aspect([placement_area.width, placement_area.height, 10])

        # 배치 정보 표시
        info_text = f"Placed: {len(placement_area.placed_blocks)}, " \
                   f"Unplaced: {len(placement_area.unplaced_blocks)}, " \
                   f"Score: {placement_area.get_placement_score():.4f}"
        ax.text2D(
            0.5, 0.05,
            info_text,
            ha='center', va='center',
            transform=ax.transAxes,
            fontsize=10
        )

        plt.tight_layout()

        # 그림 저장
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        # 그림 표시
        if show:
            plt.show()
        else:
            plt.close()

        return fig

    def compare_blocks(self, original_blocks, placement_area, title="Block Placement Comparison", show=True, save_path=None):
        """
        원본 블록과 배치 결과 비교 시각화

        Args:
            original_blocks (list): 원본 블록 목록
            placement_area (PlacementArea): 배치 영역
            title (str): 그래프 제목
            show (bool): 그래프 표시 여부
            save_path (str): 저장 경로 (None인 경우 저장하지 않음)

        Returns:
            matplotlib.figure.Figure: 생성된 그림 객체
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))
        plt.subplots_adjust(wspace=0.3)  # 서브플롯 간 간격 조정

        # 원본 블록 표시 (왼쪽)
        # 블록들을 가로로 나열하기 위한 설정
        max_block_width = max(block.width for block in original_blocks)
        max_block_height = max(block.height for block in original_blocks)

        # 가로로 몇 개의 블록을 배치할지 계산
        blocks_per_row = min(5, len(original_blocks))  # 한 줄에 최대 5개
        rows = (len(original_blocks) + blocks_per_row - 1) // blocks_per_row

        # 전체 그리드 크기 계산
        total_width = blocks_per_row * (max_block_width + 2)  # 블록 사이 간격 2
        total_height = rows * (max_block_height + 2)  # 블록 사이 간격 2

        ax1.set_xlim(0, total_width)
        ax1.set_ylim(0, total_height)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.set_aspect('equal')  # 정사각형 셀을 위한 동일한 축 비율 설정

        # 각 블록을 순서대로 나열
        for i, block in enumerate(original_blocks):
            color = self._get_block_color(block.id)

            # 블록 위치 계산 (가로로 나열)
            row = i // blocks_per_row
            col = i % blocks_per_row

            # 블록의 시작 위치 계산
            start_x = col * (max_block_width + 2) + 1  # 왼쪽 여백 1
            start_y = (rows - 1 - row) * (max_block_height + 2) + 1  # 아래쪽 여백 1

            # 블록의 중심 위치 계산 (블록을 중앙에 배치)
            center_x = start_x + (max_block_width - block.width) // 2
            center_y = start_y + (max_block_height - block.height) // 2

            # 블록의 복셀 데이터 사용
            footprint = block.get_footprint()

            # 각 복셀 표시
            for vx, vy in footprint:
                # 블록 좌표를 그리드 좌표로 변환
                grid_x = center_x + (vx - block.min_x)
                grid_y = center_y + (vy - block.min_y)

                rect = patches.Rectangle(
                    (grid_x, grid_y),
                    1, 1,
                    linewidth=1,
                    edgecolor='black',
                    facecolor=color,
                    alpha=0.8
                )
                ax1.add_patch(rect)

            # 블록 ID 표시 (블록 중앙에)
            ax1.text(
                center_x + block.width / 2,
                center_y + block.height / 2,
                block.id,
                ha='center', va='center',
                fontsize=10, fontweight='bold'
            )

        ax1.set_title("Original Blocks")

        # 배치 결과 표시 (오른쪽)
        ax2.set_xlim(0, placement_area.width)
        ax2.set_ylim(0, placement_area.height)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.set_aspect('equal')  # 정사각형 셀을 위한 동일한 축 비율 설정

        # 배치된 블록 표시
        for block_id, block in placement_area.placed_blocks.items():
            color = self._get_block_color(block_id)

            # 블록의 바닥 면적 계산
            footprint = block.get_positioned_footprint()

            # 각 복셀 표시
            for x, y in footprint:
                rect = patches.Rectangle(
                    (x, y), 1, 1,
                    linewidth=1,
                    edgecolor='black',
                    facecolor=color,
                    alpha=0.8
                )
                ax2.add_patch(rect)

                # 블록 ID 표시 (첫 번째 복셀에만)
                if (x, y) == next(iter(footprint)):
                    ax2.text(
                        x + 0.5, y + 0.5,
                        block_id,
                        ha='center', va='center',
                        fontsize=8, fontweight='bold'
                    )

        # 미배치 블록 표시 (오른쪽 하단)
        if placement_area.unplaced_blocks:
            unplaced_text = "Unplaced: " + ", ".join(placement_area.unplaced_blocks.keys())
            ax2.text(
                0.5, -0.05,
                unplaced_text,
                ha='center', va='center',
                transform=ax2.transAxes,
                fontsize=10,
                color='red'
            )

        ax2.set_title("Placement Result")

        # 배치 정보 표시
        info_text = f"Placed: {len(placement_area.placed_blocks)}, " \
                   f"Unplaced: {len(placement_area.unplaced_blocks)}, " \
                   f"Score: {placement_area.get_placement_score():.4f}"
        fig.suptitle(f"{title}\n{info_text}", fontsize=14)

        plt.tight_layout()

        # 그림 저장
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        # 그림 표시
        if show:
            plt.show()
        else:
            plt.close()

        return fig
