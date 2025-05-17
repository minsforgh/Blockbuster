"""
블록 및 복셀 데이터 구조를 정의하는 모듈
"""
import numpy as np
import copy


class VoxelBlock:
    """
    2.5D 복셀화 표현을 사용한 블록 클래스

    Attributes:
        id (str): 블록 식별자
        voxel_data (list): 복셀 데이터 [(x, y, [empty_below, filled, empty_above]), ...]
        rotation (int): 블록 회전 각도 (0 또는 180)
        position (tuple): 배치된 위치 (x, y), 배치되지 않은 경우 None
    """

    def __init__(self, id, voxel_data):
        """
        VoxelBlock 초기화

        Args:
            id (str): 블록 식별자
            voxel_data (list): 복셀 데이터 [(x, y, [empty_below, filled, empty_above]), ...]
        """
        self.id = id
        self.voxel_data = voxel_data  # [(x, y, [empty_below, filled, empty_above]), ...]
        self.rotation = 0  # 0 또는 180
        self.position = None  # 배치된 위치 (x, y), 배치되지 않은 경우 None

        # 블록의 경계 계산
        self._calculate_bounds()

    def _calculate_bounds(self):
        """블록의 경계(width, height) 계산"""
        if not self.voxel_data:
            self.width = 0
            self.height = 0
            self.min_x = 0
            self.min_y = 0
            return

        x_coords = [voxel[0] for voxel in self.voxel_data]
        y_coords = [voxel[1] for voxel in self.voxel_data]

        self.min_x = min(x_coords)
        self.min_y = min(y_coords)
        self.max_x = max(x_coords)
        self.max_y = max(y_coords)

        self.width = self.max_x - self.min_x + 1
        self.height = self.max_y - self.min_y + 1

    def rotate(self):
        """
        블록을 180도 회전
        복셀 데이터의 좌표를 변환하여 회전 처리
        """
        # 회전 상태 업데이트
        self.rotation = (self.rotation + 180) % 360

        # 복셀 데이터 회전 처리
        rotated_data = []

        # 현재 블록의 중심점 계산
        center_x = (self.min_x + self.max_x) / 2
        center_y = (self.min_y + self.max_y) / 2

        for x, y, heights in self.voxel_data:
            # 중심점 기준으로 180도 회전 (x, y) -> (-x, -y) + 중심점 보정
            new_x = int(2 * center_x - x)
            new_y = int(2 * center_y - y)
            rotated_data.append((new_x, new_y, heights))

        self.voxel_data = rotated_data
        self._calculate_bounds()

    def get_footprint(self):
        """
        블록의 바닥 면적(발자국) 반환

        Returns:
            set: (x, y) 좌표 집합
        """
        return {(voxel[0], voxel[1]) for voxel in self.voxel_data}

    def get_height_at(self, x, y):
        """
        지정된 (x, y) 위치에서의 블록 높이 반환

        Args:
            x (int): x 좌표
            y (int): y 좌표

        Returns:
            list or None: [empty_below, filled, empty_above] 또는 해당 위치에 블록이 없는 경우 None
        """
        for vx, vy, heights in self.voxel_data:
            if vx == x and vy == y:
                return heights
        return None

    def get_total_volume(self):
        """
        블록의 총 부피 계산

        Returns:
            int: 블록의 총 부피 (채워진 공간의 합)
        """
        return sum(heights[1] for _, _, heights in self.voxel_data)

    def get_area(self):
        """
        블록의 바닥 면적 계산

        Returns:
            int: 블록의 바닥 면적 (복셀 수)
        """
        return len(self.voxel_data)

    def get_positioned_footprint(self):
        """
        배치된 위치를 고려한 블록의 바닥 면적 반환

        Returns:
            set: 배치된 위치에서의 (x, y) 좌표 집합, 배치되지 않은 경우 None
        """
        if self.position is None:
            return None

        pos_x, pos_y = self.position
        return {(pos_x + voxel[0] - self.min_x, pos_y + voxel[1] - self.min_y)
                for voxel in self.voxel_data}

    def get_positioned_voxels(self):
        """
        배치된 위치를 고려한 블록의 복셀 데이터 반환

        Returns:
            list: 배치된 위치에서의 [(x, y, [empty_below, filled, empty_above]), ...],
                  배치되지 않은 경우 None
        """
        if self.position is None:
            return None

        pos_x, pos_y = self.position
        return [(pos_x + voxel[0] - self.min_x, pos_y + voxel[1] - self.min_y, voxel[2])
                for voxel in self.voxel_data]

    def clone(self):
        """
        블록의 복제본 생성

        Returns:
            VoxelBlock: 현재 블록의 복제본
        """
        # 깊은 복사를 사용하여 복셀 데이터 복제
        new_block = VoxelBlock(self.id, copy.deepcopy(self.voxel_data))

        # 회전 상태 복제
        new_block.rotation = self.rotation

        # 위치 복제 (None이 아닌 경우에만)
        if self.position is not None:
            new_block.position = tuple(self.position)  # 튜플로 복제하여 불변성 보장
        else:
            new_block.position = None

        # 경계 계산 (이미 생성자에서 수행됨)

        return new_block

    def __str__(self):
        """블록 정보 문자열 표현"""
        return f"Block {self.id}: {len(self.voxel_data)} voxels, " \
               f"size: {self.width}x{self.height}, rotation: {self.rotation}°"
