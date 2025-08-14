"""
배치 영역 관리를 위한 모듈
"""
import numpy as np
import copy


class PlacementArea:
    """
    블록 배치 영역 관리 클래스

    Attributes:
        width (int): 배치 영역의 너비
        height (int): 배치 영역의 높이
        grid (numpy.ndarray): 배치 상태를 저장하는 그리드
        placed_blocks (dict): 배치된 블록 정보 {block_id: block}
        unplaced_blocks (dict): 미배치된 블록 정보 {block_id: block}
    """

    def __init__(self, width, height):
        """
        PlacementArea 초기화

        Args:
            width (int): 배치 영역의 너비
            height (int): 배치 영역의 높이
        """
        self.width = width
        self.height = height
        # 각 셀에는 해당 위치에 배치된 블록의 ID가 저장됨
        self.grid = np.full((height, width), None, dtype=object)
        self.placed_blocks = {}  # {block_id: block}
        self.unplaced_blocks = {}  # {block_id: block}

        # 트랜스포터 진입 경로 관리를 위한 그리드
        self.path_grid = np.zeros((height, width), dtype=int)

    def add_blocks(self, blocks):
        """
        배치할 블록 목록 추가

        Args:
            blocks (list): VoxelBlock 객체 목록
        """
        for block in blocks:
            self.unplaced_blocks[block.id] = block

    def can_place_block(self, block, pos_x, pos_y):
        """
        해당 위치에 블록 배치 가능 여부 확인

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표
            pos_y (int): 배치 위치 y 좌표

        Returns:
            bool: 배치 가능 여부
        """
        # 블록의 바닥 면적 계산
        footprint = block.get_footprint()

        # 배치 영역 내에 있는지 확인
        for vx, vy in footprint:
            # 블록 좌표를 배치 영역 좌표로 변환
            grid_x = pos_x + vx - block.min_x
            grid_y = pos_y + vy - block.min_y

            # 배치 영역을 벗어나는지 확인
            if grid_x < 0 or grid_x >= self.width or grid_y < 0 or grid_y >= self.height:
                return False

            # 다른 블록과 겹치는지 확인
            if self.grid[grid_y, grid_x] is not None:
                return False

        # 트랜스포터 진입 가능성 확인
        if not self._check_transporter_access(block, pos_x, pos_y):
            return False

        return True

    def _check_transporter_access(self, block, pos_x, pos_y):
        """
        블록 접근성 확인
        - 크레인 블록: 수직으로 내려놓을 수 있어서 경로 확보 불필요
        - 트레슬 블록: 오른쪽에서 Y길이만큼 경로 폭 확보 필요
        - 기타: 트레슬 블록과 동일한 조건

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표  
            pos_y (int): 배치 위치 y 좌표

        Returns:
            bool: 블록 접근 가능 여부
        """
        # 크레인 블록은 수직으로 내려놓을 수 있어서 경로 확보 불필요
        if hasattr(block, 'block_type') and block.block_type == 'crane':
            return True  # 크레인 블록은 항상 접근 가능
        
        # 트레슬 블록과 기타 블록은 트랜스포터 경로 확보 필요
        # 블록의 Y 범위만 체크 (어제 버전과 동일)
        block_y_start = pos_y
        block_y_end = pos_y + block.height
        
        # 배치 영역 왼쪽 끝에서 블록의 왼쪽 끝까지 경로 확인
        block_left_edge = pos_x
        
        # 왼쪽 끝에서 블록 위치까지 쭉 밀어넣을 수 있는지 확인 (Y 여유 포함)
        for x in range(0, block_left_edge):
            for y in range(block_y_start, block_y_end):
                if y < 0 or y >= self.height or self.grid[y, x] is not None:
                    return False
        
        return True

    def _has_path_to_edge(self, grid, start_x, start_y):
        """
        시작 위치에서 가장자리까지 경로가 있는지 확인 (BFS)

        Args:
            grid (numpy.ndarray): 배치 상태 그리드
            start_x (int): 시작 위치 x 좌표
            start_y (int): 시작 위치 y 좌표

        Returns:
            bool: 가장자리까지 경로 존재 여부
        """
        from collections import deque

        # 이미 가장자리인 경우
        if start_x == 0 or start_x == self.width - 1 or start_y == 0 or start_y == self.height - 1:
            return True

        # BFS를 위한 큐 초기화
        queue = deque([(start_x, start_y)])
        visited = np.zeros((self.height, self.width), dtype=bool)
        visited[start_y, start_x] = True

        while queue:
            x, y = queue.popleft()

            # 4방향 탐색
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy

                # 배치 영역 내에 있는지 확인
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    # 가장자리에 도달한 경우
                    if nx == 0 or nx == self.width - 1 or ny == 0 or ny == self.height - 1:
                        return True

                    # 빈 공간이고 방문하지 않은 경우
                    if grid[ny, nx] is None and not visited[ny, nx]:
                        queue.append((nx, ny))
                        visited[ny, nx] = True

        return False

    def place_block(self, block, pos_x, pos_y):
        """
        블록을 해당 위치에 배치

        Args:
            block (VoxelBlock): 배치할 블록
            pos_x (int): 배치 위치 x 좌표
            pos_y (int): 배치 위치 y 좌표

        Returns:
            bool: 배치 성공 여부
        """
        if not self.can_place_block(block, pos_x, pos_y):
            return False

        # 블록 위치 설정
        block.position = (pos_x, pos_y)

        # 그리드에 블록 배치
        footprint = block.get_footprint()
        for vx, vy in footprint:
            grid_x = pos_x + vx - block.min_x
            grid_y = pos_y + vy - block.min_y
            self.grid[grid_y, grid_x] = block.id

        # 배치된 블록 목록 업데이트
        self.placed_blocks[block.id] = block
        if block.id in self.unplaced_blocks:
            del self.unplaced_blocks[block.id]

        return True

    def remove_block(self, block_id):
        """
        배치된 블록 제거 (백트래킹용)

        Args:
            block_id (str): 제거할 블록 ID

        Returns:
            bool: 제거 성공 여부
        """
        if block_id not in self.placed_blocks:
            return False

        block = self.placed_blocks[block_id]

        # 그리드에서 블록 제거
        footprint = block.get_positioned_footprint()
        for x, y in footprint:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.grid[y, x] = None

        # 블록 위치 초기화
        block.position = None

        # 배치된 블록 목록 업데이트
        del self.placed_blocks[block_id]
        self.unplaced_blocks[block_id] = block

        return True

    def get_placement_score(self):
        """
        현재 배치 상태의 점수 계산

        Returns:
            float: 배치 점수 (높을수록 좋음)
        """
        # 배치된 블록의 총 면적
        placed_area = sum(block.get_area() for block in self.placed_blocks.values())

        # 배치된 블록의 비율
        placement_ratio = len(self.placed_blocks) / (len(self.placed_blocks) + len(self.unplaced_blocks)) if self.placed_blocks or self.unplaced_blocks else 0

        # 공간 활용률
        space_utilization = placed_area / (self.width * self.height)

        # 가중치를 적용한 종합 점수
        score = 0.5 * placement_ratio + 0.5 * space_utilization

        return score

    def clone(self):
        """
        배치 영역의 복제본 생성

        Returns:
            PlacementArea: 현재 배치 영역의 복제본
        """
        new_area = PlacementArea(self.width, self.height)
        new_area.grid = np.copy(self.grid)

        # 블록 복제
        for block_id, block in self.placed_blocks.items():
            new_area.placed_blocks[block_id] = block.clone()

        for block_id, block in self.unplaced_blocks.items():
            new_area.unplaced_blocks[block_id] = block.clone()

        return new_area

    def __str__(self):
        """배치 영역 정보 문자열 표현"""
        return f"PlacementArea {self.width}x{self.height}: " \
               f"{len(self.placed_blocks)} placed, {len(self.unplaced_blocks)} unplaced"
