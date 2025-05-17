"""
백트래킹 기반 블록 배치 알고리즘 모듈
"""
import time
import copy
from algorithms.candidate_generator import CandidateGenerator


class BacktrackingPlacer:
    """
    백트래킹 기반 블록 배치 알고리즘 클래스

    Attributes:
        placement_area (PlacementArea): 배치 영역
        blocks (list): 배치할 블록 목록
        candidate_generator (CandidateGenerator): 후보 위치 생성기
        best_solution (PlacementArea): 최적 배치 결과
        best_score (float): 최적 배치 점수
        max_time (float): 최대 실행 시간 (초)
        start_time (float): 알고리즘 시작 시간
    """

    def __init__(self, placement_area, blocks, max_time=60):
        """
        BacktrackingPlacer 초기화

        Args:
            placement_area (PlacementArea): 배치 영역
            blocks (list): 배치할 블록 목록
            max_time (float): 최대 실행 시간 (초)
        """
        self.placement_area = placement_area
        self.blocks = blocks
        self.candidate_generator = CandidateGenerator(placement_area)
        self.best_solution = None
        self.best_score = 0
        self.max_time = max_time
        self.start_time = 0

        # 배치 영역에 블록 추가
        self.placement_area.add_blocks(blocks)

    def optimize(self):
        """
        백트래킹을 통한 최적 배치 탐색

        Returns:
            PlacementArea: 최적 배치 결과
        """
        self.start_time = time.time()
        self.best_solution = None
        self.best_score = 0

        # 블록 배치 순서 결정 (복합 기준)
        # 1. 넓은 블록 우선 (너비 기준) - X축 방향으로 먼저 채우기 위함
        # 2. 대형 블록 우선 (면적 기준)
        # 3. 복잡한 모양 우선 (면적 대비 복셀 수)
        sorted_blocks = sorted(
            self.blocks,
            key=lambda block: (
                block.width,  # 1차 기준: 너비 (X축 방향 우선)
                block.get_area(),  # 2차 기준: 면적
                block.get_area() / (block.width * block.height)  # 3차 기준: 밀도
            ),
            reverse=True
        )

        # 초기 상태 설정
        initial_area = copy.deepcopy(self.placement_area)

        # 백트래킹 시작
        self._backtrack(initial_area, sorted_blocks, 0)

        return self.best_solution

    def _backtrack(self, current_area, sorted_blocks, depth):
        """
        재귀적 백트래킹 함수

        Args:
            current_area (PlacementArea): 현재 배치 상태
            sorted_blocks (list): 정렬된 블록 목록
            depth (int): 현재 탐색 깊이
        """
        # 시간 제한 확인
        if time.time() - self.start_time > self.max_time:
            return

        # 현재 배치 상태의 점수 계산
        current_score = current_area.get_placement_score()

        # 최적해 업데이트
        if current_score > self.best_score:
            self.best_score = current_score
            self.best_solution = copy.deepcopy(current_area)

        # 모든 블록이 배치된 경우
        if depth >= len(sorted_blocks):
            return

        # 현재 배치할 블록
        current_block = sorted_blocks[depth]

        # 후보 위치 생성
        candidates = self.candidate_generator.generate_candidates(current_block)

        # 각 후보 위치에 대해 시도
        for pos_x, pos_y, rotation, _ in candidates:
            # 원본 회전 상태 저장
            original_rotation = current_block.rotation

            # 블록 회전 설정
            if current_block.rotation != rotation:
                current_block.rotate()

            # 블록 배치 시도
            if current_area.place_block(current_block, pos_x, pos_y):
                # 다음 블록으로 진행
                self._backtrack(current_area, sorted_blocks, depth + 1)

                # 백트래킹: 블록 제거
                current_area.remove_block(current_block.id)

            # 블록 회전 복원 (원래 상태로)
            while current_block.rotation != original_rotation:
                current_block.rotate()

        # 현재 블록을 배치하지 않고 다음 블록으로 진행
        # 이렇게 하면 특정 블록을 건너뛰고 다른 블록을 배치할 수 있음
        self._backtrack(current_area, sorted_blocks, depth + 1)

        # 현재 블록을 배치하지 않고 다음 블록으로 진행 (선택적)
        # 이 부분은 모든 블록을 반드시 배치해야 하는 경우 주석 처리
        # self._backtrack(current_area, sorted_blocks, depth + 1)


