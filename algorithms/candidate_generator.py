"""
블록 배치 후보 위치 생성기 모듈 (Y축 우선으로 수정)
"""
import numpy as np


class CandidateGenerator:
    """
    블록 배치 후보 위치 생성기 클래스 (Y축 우선)
    BinPacking 기반 후보 위치 생성 및 휴리스틱 점수 계산

    Attributes:
        placement_area (PlacementArea): 배치 영역
    """

    def __init__(self, placement_area):
        """
        CandidateGenerator 초기화

        Args:
            placement_area (PlacementArea): 배치 영역
        """
        self.placement_area = placement_area

    def generate_candidates(self, block, consider_rotation=True):
        """
        블록에 대한 배치 후보 위치 생성

        Args:
            block (VoxelBlock): 배치할 블록
            consider_rotation (bool): 회전 고려 여부

        Returns:
            list: (pos_x, pos_y, rotation, score) 형태의 후보 위치 목록
        """
        candidates = []

        # 원본 방향으로 후보 위치 생성
        original_candidates = self._generate_candidates_for_orientation(block)
        candidates.extend(original_candidates)

        # 회전 고려
        if consider_rotation:
            # 블록 회전
            original_rotation = block.rotation
            block.rotate()

            # 회전된 방향으로 후보 위치 생성
            rotated_candidates = self._generate_candidates_for_orientation(block)
            candidates.extend(rotated_candidates)

            # 블록 원래 방향으로 복원
            block.rotation = original_rotation

        # 중복 제거
        unique_candidates = []
        seen = set()
        for x, y, rotation, score in candidates:
            key = (x, y, rotation)
            if key not in seen:
                seen.add(key)
                unique_candidates.append((x, y, rotation, score))

        # 점수에 따라 후보 위치 정렬 (내림차순)
        unique_candidates.sort(key=lambda x: x[3], reverse=True)

        return unique_candidates

    def _generate_candidates_for_orientation(self, block):
        """
        현재 블록 방향에 대한 후보 위치 생성 (Y축 우선으로 수정)

        Args:
            block (VoxelBlock): 배치할 블록

        Returns:
            list: (pos_x, pos_y, rotation, score) 형태의 후보 위치 목록
        """
        candidates = []

        # BinPacking 기반 후보 위치 생성 (Y축 우선으로 수정)
        # 1. 위쪽 왼쪽 모서리 우선 배치 (Top-Left 전략)
        # 2. 기존 블록에 인접한 위치 우선 배치 (Adjacent 전략)
        # 3. 배치 영역 경계 우선 배치 (Boundary 전략)

        # 배치 영역 전체 탐색 (Y축 우선 배치를 위해 X축 먼저 순회)
        for x in range(self.placement_area.width):
            for y in range(self.placement_area.height):
                # 해당 위치에 블록 배치 가능 여부 확인
                if self.placement_area.can_place_block(block, x, y):
                    # 휴리스틱 점수 계산
                    score = self._calculate_heuristic_score(block, x, y)

                    # X값이 작을수록 높은 점수 부여 (Y축 방향 우선 배치)
                    x_bonus = 1.0 - (x / self.placement_area.width)
                    score *= (1.0 + x_bonus)

                    candidates.append((x, y, block.rotation, score))

        # 특별한 위치 추가: 이미 배치된 블록에 인접한 위치
        for placed_block_id, placed_block in self.placement_area.placed_blocks.items():
            if placed_block.position is None:
                continue

            placed_x, placed_y = placed_block.position
            footprint = placed_block.get_positioned_footprint()

            # 배치된 블록 주변 위치 탐색
            for x, y in footprint:
                # 8방향 확인 (대각선 포함)
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                    nx, ny = x + dx, y + dy

                    # 배치 영역 내에 있고 비어있는 위치인 경우
                    if (0 <= nx < self.placement_area.width and
                        0 <= ny < self.placement_area.height and
                        self.placement_area.grid[ny, nx] is None):

                        # 해당 위치에 블록 배치 가능 여부 확인
                        if self.placement_area.can_place_block(block, nx, ny):
                            # 휴리스틱 점수 계산 (인접성 가중치 증가)
                            score = self._calculate_heuristic_score(block, nx, ny) * 1.2  # 인접 위치 가중치 20% 증가
                            candidates.append((nx, ny, block.rotation, score))

        # 특별한 위치 추가: 빈 공간 채우기
        # 배치 영역의 빈 공간을 찾아 블록 배치 시도
        empty_spaces = self._find_empty_spaces()
        for space_x, space_y, space_width, space_height in empty_spaces:
            # 빈 공간에 블록 배치 가능 여부 확인
            if (space_width >= block.width and space_height >= block.height and
                self.placement_area.can_place_block(block, space_x, space_y)):
                # 휴리스틱 점수 계산 (빈 공간 채우기 가중치 증가)
                score = self._calculate_heuristic_score(block, space_x, space_y) * 1.5  # 빈 공간 채우기 가중치 50% 증가
                candidates.append((space_x, space_y, block.rotation, score))

        # 중복 제거
        unique_candidates = []
        seen = set()
        for x, y, rotation, score in candidates:
            key = (x, y, rotation)
            if key not in seen:
                seen.add(key)
                unique_candidates.append((x, y, rotation, score))

        return unique_candidates

    def _find_empty_spaces(self):
        """
        배치 영역의 빈 공간 찾기 (Y축 우선으로 수정)

        Returns:
            list: (x, y, width, height) 형태의 빈 공간 목록
        """
        empty_spaces = []
        grid = self.placement_area.grid
        width = self.placement_area.width
        height = self.placement_area.height

        # 빈 공간 찾기 (Y축 우선 순서로)
        for x in range(width):
            for y in range(height):
                # 이미 블록이 배치된 위치는 건너뜀
                if grid[y, x] is not None:
                    continue

                # 빈 공간의 너비와 높이 계산
                max_width = 1
                max_height = 1

                # 너비 계산
                for w in range(1, width - x):
                    if x + w < width and grid[y, x + w] is None:
                        max_width = w + 1
                    else:
                        break

                # 높이 계산
                for h in range(1, height - y):
                    is_empty_row = True
                    for w in range(max_width):
                        if y + h < height and x + w < width and grid[y + h, x + w] is None:
                            continue
                        else:
                            is_empty_row = False
                            break

                    if is_empty_row:
                        max_height = h + 1
                    else:
                        break

                # 빈 공간 추가
                if max_width > 1 or max_height > 1:
                    # Y축 방향 우선 배치를 위해 X값이 작은 빈 공간 우선
                    # X값이 같은 경우 Y값이 작은 빈 공간 우선

                    # 새로운 빈 공간 정보
                    new_space = (x, y, max_width, max_height)

                    # 빈 공간 목록에 삽입 (X값 오름차순, X값이 같으면 Y값 오름차순)
                    inserted = False
                    for i, (sx, sy, sw, sh) in enumerate(empty_spaces):
                        if x < sx or (x == sx and y < sy):
                            empty_spaces.insert(i, new_space)
                            inserted = True
                            break

                    if not inserted:
                        empty_spaces.append(new_space)

        return empty_spaces

    def _calculate_heuristic_score(self, block, pos_x, pos_y):
        """
        휴리스틱 점수 계산 (Y축 우선으로 수정)

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표
            pos_y (int): 배치 위치 y 좌표

        Returns:
            float: 휴리스틱 점수 (높을수록 좋음)
        """
        # 1. Y축 우선 배치 점수
        # Y축 방향으로 먼저 채우기 위해 X값이 작을수록 높은 점수
        y_first_score = 1.0 - (pos_x / self.placement_area.width)

        # 2. 위쪽 정렬 점수 (Top 전략)
        # 위쪽에 가까울수록 높은 점수
        top_alignment_score = 1.0 - (pos_y / self.placement_area.height)

        # 3. 인접성 점수 (Adjacent 전략)
        # 다른 블록과 인접할수록 높은 점수
        adjacency_score = self._calculate_adjacency_score(block, pos_x, pos_y)

        # 4. 면적 활용 점수
        # 블록의 면적이 클수록 높은 점수
        area_score = block.get_area() / (self.placement_area.width * self.placement_area.height)

        # 5. 경계 활용 점수
        # 배치 영역의 경계에 인접할수록 높은 점수
        boundary_score = self._calculate_boundary_score(block, pos_x, pos_y)

        # 6. 공간 효율성 점수
        # 블록이 차지하는 공간이 조밀할수록 높은 점수
        density_score = block.get_area() / (block.width * block.height)

        # 가중치를 적용한 종합 점수 (Y축 우선에 맞게 조정)
        score = (
            0.4 * y_first_score +      # Y축 우선 배치에 높은 가중치
            0.2 * top_alignment_score +  # 위쪽 정렬에 가중치
            0.2 * adjacency_score +
            0.1 * area_score +
            0.05 * boundary_score +
            0.05 * density_score
        )

        return score

    def _calculate_adjacency_score(self, block, pos_x, pos_y):
        """
        인접성 점수 계산

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표
            pos_y (int): 배치 위치 y 좌표

        Returns:
            float: 인접성 점수 (0~1, 높을수록 좋음)
        """
        adjacent_count = 0
        total_perimeter = 0

        # 블록의 바닥 면적 계산
        footprint = block.get_footprint()

        for vx, vy in footprint:
            # 블록 좌표를 배치 영역 좌표로 변환
            grid_x = pos_x + vx - block.min_x
            grid_y = pos_y + vy - block.min_y

            # 배치 영역 내에 있는지 확인
            if 0 <= grid_x < self.placement_area.width and 0 <= grid_y < self.placement_area.height:
                # 4방향 확인
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = grid_x + dx, grid_y + dy

                    # 배치 영역 내에 있고 다른 블록과 인접한 경우
                    if 0 <= nx < self.placement_area.width and 0 <= ny < self.placement_area.height:
                        total_perimeter += 1
                        if self.placement_area.grid[ny, nx] is not None:
                            adjacent_count += 1

        # 인접성 점수 계산
        return adjacent_count / total_perimeter if total_perimeter > 0 else 0

    def _calculate_boundary_score(self, block, pos_x, pos_y):
        """
        경계 활용 점수 계산

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표
            pos_y (int): 배치 위치 y 좌표

        Returns:
            float: 경계 활용 점수 (0~1, 높을수록 좋음)
        """
        boundary_count = 0
        total_perimeter = 0

        # 블록의 바닥 면적 계산
        footprint = block.get_footprint()

        for vx, vy in footprint:
            # 블록 좌표를 배치 영역 좌표로 변환
            grid_x = pos_x + vx - block.min_x
            grid_y = pos_y + vy - block.min_y

            # 배치 영역 내에 있는지 확인
            if 0 <= grid_x < self.placement_area.width and 0 <= grid_y < self.placement_area.height:
                # 4방향 확인
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nx, ny = grid_x + dx, grid_y + dy

                    total_perimeter += 1

                    # 배치 영역 경계에 인접한 경우
                    if nx < 0 or nx >= self.placement_area.width or ny < 0 or ny >= self.placement_area.height:
                        boundary_count += 1

        # 경계 활용 점수 계산
        return boundary_count / total_perimeter if total_perimeter > 0 else 0