"""
임의 블록 생성기 모듈
"""
import random
import numpy as np
from models.voxel_block import VoxelBlock


class RandomBlockGenerator:
    """
    임의의 복셀 블록 데이터 생성기 클래스

    Attributes:
        complexity (float): 블록 복잡도 (0.0~2.0)
        large_block_bias (float): 대형 블록 생성 비율 (0.0~1.0)
    """

    def __init__(self, complexity=1.0, large_block_bias=0.7):
        """
        RandomBlockGenerator 초기화

        Args:
            complexity (float): 블록 복잡도 (0.0~2.0)
            large_block_bias (float): 대형 블록 생성 비율 (0.0~1.0)
        """
        self.complexity = max(0.1, min(2.0, complexity))
        self.large_block_bias = max(0.0, min(1.0, large_block_bias))

    def generate_blocks(self, count=8, max_size=10):
        """
        임의의 복셀 블록 데이터 생성

        Args:
            count (int): 생성할 블록 수
            max_size (int): 최대 블록 크기

        Returns:
            list: 생성된 VoxelBlock 객체 목록
        """
        blocks = []

        for i in range(count):
            # 블록 ID 생성
            block_id = f"B{i+1}"

            # 블록 크기 결정 (대형 블록 비율 적용)
            if random.random() < self.large_block_bias:
                # 대형 블록 (선박 면적의 약 10~15% 차지)
                width = random.randint(max(3, int(max_size * 0.5)), max_size)
                height = random.randint(max(3, int(max_size * 0.5)), max_size)
            else:
                # 소형 블록 (선박 면적의 약 5~10% 차지)
                width = random.randint(2, max(2, int(max_size * 0.4)))
                height = random.randint(2, max(2, int(max_size * 0.4)))

            # 복셀 데이터 생성
            voxel_data = self._generate_voxel_data(width, height)

            # VoxelBlock 객체 생성
            block = VoxelBlock(block_id, voxel_data)
            blocks.append(block)

        return blocks

    def _generate_voxel_data(self, width, height):
        """
        복셀 데이터 생성

        Args:
            width (int): 블록 너비
            height (int): 블록 높이

        Returns:
            list: 복셀 데이터 [(x, y, [empty_below, filled, empty_above]), ...]
        """
        voxel_data = []

        # 블록 모양 결정 (0: 직사각형, 1: L자, 2: T자, 3: Z자, 4: U자, 5: 십자형)
        shape_type = random.randint(0, 5)

        # 직사각형 블록
        if shape_type == 0:
            for x in range(width):
                for y in range(height):
                    # 복잡도에 따라 일부 위치 제외
                    if random.random() < 0.1:  # 10% 확률로 구멍 생성
                        continue

                    heights = [0, random.randint(1, 3), 0]  # [empty_below, filled, empty_above]
                    voxel_data.append((x, y, heights))

        # L자 블록
        elif shape_type == 1:
            for x in range(width):
                for y in range(height):
                    if x < width // 2 or y < height // 2:
                        if random.random() < 0.1:  # 10% 확률로 구멍 생성
                            continue

                        heights = [0, random.randint(1, 3), 0]
                        voxel_data.append((x, y, heights))

        # T자 블록
        elif shape_type == 2:
            for x in range(width):
                for y in range(height):
                    if x == width // 2 or y < height // 2:
                        if random.random() < 0.1:  # 10% 확률로 구멍 생성
                            continue

                        heights = [0, random.randint(1, 3), 0]
                        voxel_data.append((x, y, heights))

        # Z자 블록
        elif shape_type == 3:
            for x in range(width):
                for y in range(height):
                    if (x < width // 2 and y < height // 2) or (x >= width // 2 and y >= height // 2):
                        if random.random() < 0.1:  # 10% 확률로 구멍 생성
                            continue

                        heights = [0, random.randint(1, 3), 0]
                        voxel_data.append((x, y, heights))

        # U자 블록
        elif shape_type == 4:
            for x in range(width):
                for y in range(height):
                    if y == 0 or x == 0 or x == width - 1:
                        if random.random() < 0.1:  # 10% 확률로 구멍 생성
                            continue

                        heights = [0, random.randint(1, 3), 0]
                        voxel_data.append((x, y, heights))

        # 십자형 블록
        else:
            for x in range(width):
                for y in range(height):
                    if x == width // 2 or y == height // 2:
                        if random.random() < 0.1:  # 10% 확률로 구멍 생성
                            continue

                        heights = [0, random.randint(1, 3), 0]
                        voxel_data.append((x, y, heights))

        # 빈 블록인 경우 최소 1개의 복셀 추가
        if not voxel_data:
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            heights = [0, random.randint(1, 3), 0]
            voxel_data.append((x, y, heights))

        return voxel_data

    def _generate_height_data(self):
        """
        높이 데이터 생성 [empty_below, filled, empty_above]

        Returns:
            list: [empty_below, filled, empty_above] 형태의 높이 데이터
        """
        # 복잡도에 따라 높이 데이터 생성
        if self.complexity < 1.0:
            # 낮은 복잡도: 단순한 높이 데이터
            empty_below = random.randint(0, 1)
            filled = random.randint(1, 3)
            empty_above = random.randint(0, 1)
        else:
            # 높은 복잡도: 다양한 높이 데이터
            empty_below = random.randint(0, 2)
            filled = random.randint(1, 4)
            empty_above = random.randint(0, 2)

        return [empty_below, filled, empty_above]

    def generate_predefined_blocks(self):
        """
        미리 정의된 블록 세트 생성 (테스트용)

        Returns:
            list: 생성된 VoxelBlock 객체 목록
        """
        blocks = []

        # 블록 1: 대형 L자 블록
        voxel_data_1 = []
        for x in range(4):
            for y in range(3):
                if x < 2 or y < 1:
                    voxel_data_1.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B1", voxel_data_1))

        # 블록 2: 중형 직사각형 블록
        voxel_data_2 = []
        for x in range(3):
            for y in range(2):
                voxel_data_2.append((x, y, [0, 3, 0]))
        blocks.append(VoxelBlock("B2", voxel_data_2))

        # 블록 3: 소형 정사각형 블록
        voxel_data_3 = []
        for x in range(2):
            for y in range(2):
                voxel_data_3.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B3", voxel_data_3))

        # 블록 4: T자 블록
        voxel_data_4 = []
        for x in range(3):
            for y in range(3):
                if x == 1 or y == 0:
                    voxel_data_4.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B4", voxel_data_4))

        # 블록 5: 중형 직사각형 블록
        voxel_data_5 = []
        for x in range(4):
            for y in range(2):
                voxel_data_5.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B5", voxel_data_5))

        # 블록 6: 중형 Z자 블록
        voxel_data_6 = []
        for x in range(3):
            for y in range(3):
                if (x < 2 and y < 2) or (x > 0 and y > 0):
                    voxel_data_6.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B6", voxel_data_6))

        # 블록 7: 소형 L자 블록
        voxel_data_7 = []
        for x in range(2):
            for y in range(3):
                if x == 0 or y == 0:
                    voxel_data_7.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B7", voxel_data_7))

        # 블록 8: 중형 U자 블록
        voxel_data_8 = []
        for x in range(3):
            for y in range(3):
                if y == 0 or x == 0 or x == 2:
                    voxel_data_8.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B8", voxel_data_8))

        # 블록 9: 십자 블록
        voxel_data_9 = []
        for x in range(3):
            for y in range(3):
                if x == 1 or y == 1:
                    voxel_data_9.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B9", voxel_data_9))

        # 블록 10: H자 블록
        voxel_data_10 = []
        for x in range(3):
            for y in range(3):
                if x == 0 or x == 2 or y == 1:
                    voxel_data_10.append((x, y, [0, 2, 0]))
        blocks.append(VoxelBlock("B10", voxel_data_10))

        return blocks
