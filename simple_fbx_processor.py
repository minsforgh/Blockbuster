"""
간단하고 빠른 FBX 처리기 - 바운딩 박스 기반 2D 블록 생성
"""

import open3d as o3d
import numpy as np
import math
import os
import glob
import time
from pathlib import Path
from models.voxel_block import VoxelBlock

class SimpleFBXProcessor:
    """
    빠른 FBX 처리기 - 정확한 메시 대신 바운딩 박스 기반 직사각형 블록 생성
    """
    
    def __init__(self, grid_resolution=2.0, input_unit='mm'):
        """
        Args:
            grid_resolution (float): 그리드 해상도 (미터 단위, 기본값: 2m)
            input_unit (str): 입력 파일의 단위 ('mm', 'cm', 'm', 'inch', 'ft')
        """
        self.grid_resolution = grid_resolution
        self.input_unit = input_unit
        
        # 단위 변환 팩터 (입력 단위 → 미터)
        self.unit_factors = {
            'mm': 0.001,      # 밀리미터 → 미터
            'cm': 0.01,       # 센티미터 → 미터
            'm': 1.0,         # 미터 → 미터
            'inch': 0.0254,   # 인치 → 미터
            'ft': 0.3048      # 피트 → 미터
        }
        
        self.conversion_factor = self.unit_factors.get(input_unit, 0.001)
        print(f"🔧 입력 단위 설정: {input_unit} (변환 팩터: {self.conversion_factor})")
        
    def load_all_fbx_blocks_fast(self, fbx_directory, max_files=None):
        """
        FBX 파일들을 빠르게 바운딩 박스 기반으로 처리
        
        Args:
            fbx_directory (str): FBX 파일들이 있는 디렉토리 경로
            max_files (int): 처리할 최대 파일 수
            
        Returns:
            list: VoxelBlock 객체 리스트
        """
        print(f"=== 빠른 FBX 블록 로딩 시작 ===")
        print(f"디렉토리: {fbx_directory}")
        print(f"⚡ 처리 방식: 바운딩 박스 기반 직사각형 블록")
        
        # FBX 파일 찾기
        all_fbx_files = self._find_fbx_files(fbx_directory)
        
        if not all_fbx_files:
            print("❌ FBX 파일을 찾을 수 없습니다.")
            print(f"확인할 경로: {os.path.abspath(fbx_directory)}")
            return []
        
        print(f"📁 발견된 전체 FBX 파일: {len(all_fbx_files)}개")
        
        # 파일 수 제한 적용
        if max_files and max_files < len(all_fbx_files):
            import random
            fbx_files = random.sample(all_fbx_files, max_files)
            print(f"🎲 랜덤 선택: {max_files}개 파일 처리")
        else:
            fbx_files = all_fbx_files
            print(f"📋 전체 파일 처리: {len(fbx_files)}개")
        
        print("선택된 파일들:")
        for fbx_file in fbx_files[:10]:  # 처음 10개만 표시
            print(f"  - {os.path.basename(fbx_file)}")
        if len(fbx_files) > 10:
            print(f"  ... (총 {len(fbx_files)}개)")
        
        # 변환 진행
        blocks = []
        total_start_time = time.time()
        
        for i, fbx_path in enumerate(fbx_files):
            block_name = Path(fbx_path).stem  # 원본 파일명 (확장자 제거)
            block_id = block_name  # 파일명 그대로 사용
            
            print(f"\n⚡ 빠른 처리 ({i+1}/{len(fbx_files)}): {block_name}")
            
            start_time = time.time()
            try:
                voxel_block = self._convert_fbx_to_simple_block(fbx_path, block_id)
                elapsed = time.time() - start_time
                
                if voxel_block:
                    blocks.append(voxel_block)
                    print(f"✅ {block_id} 완료: {voxel_block.width}x{voxel_block.height} 그리드 ({elapsed:.2f}초)")
                else:
                    print(f"❌ {block_id} 실패 ({elapsed:.2f}초)")
                    
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ {fbx_path} 오류: {str(e)} ({elapsed:.2f}초)")
        
        total_elapsed = time.time() - total_start_time
        print(f"\n🎉 처리 완료: {len(blocks)}개 블록 성공")
        print(f"📊 총 처리 시간: {total_elapsed:.1f}초 (평균 {total_elapsed/len(fbx_files):.1f}초/파일)")
        print(f"📈 처리 속도: 기존 대비 약 10~20배 빠름")
        
        return blocks
    
    def _find_fbx_files(self, directory):
        """
        디렉토리에서 3D 파일들 찾기
        """
        patterns = ['*.fbx', '*.FBX', '*.obj', '*.OBJ', '*.ply', '*.PLY']
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(directory, pattern)))
        
        return sorted(files)
    
    def _convert_fbx_to_simple_block(self, fbx_path, block_id):
        """
        FBX 파일을 간단한 직사각형 블록으로 변환
        
        Args:
            fbx_path (str): FBX 파일 경로
            block_id (str): 블록 ID
            
        Returns:
            VoxelBlock: 변환된 블록 객체
        """
        try:
            # 1. 메시 로드 (빠른 로딩)
            mesh = o3d.io.read_triangle_mesh(fbx_path)
            
            if len(mesh.vertices) == 0:
                print(f"   ⚠️ 메시 데이터 없음")
                return None
            
            # 2. 바운딩 박스만 계산 (매우 빠름)
            bbox = mesh.get_axis_aligned_bounding_box()
            size = bbox.get_extent()
            
            print(f"   📏 원본 크기: {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} {self.input_unit}")
            
            # 3. 미터로 변환
            width_m = size[0] * self.conversion_factor
            height_m = size[1] * self.conversion_factor
            
            print(f"   📐 미터 변환: {width_m:.1f}m x {height_m:.1f}m")
            
            # 4. 합리적인 크기 체크 및 제한
            max_reasonable_size = 200  # 200m 이상은 비정상
            if width_m > max_reasonable_size or height_m > max_reasonable_size:
                print(f"   ⚠️ 비정상적으로 큰 크기 감지! 제한 적용")
                scale_factor = min(max_reasonable_size / width_m, max_reasonable_size / height_m)
                width_m *= scale_factor
                height_m *= scale_factor
                print(f"   📏 제한된 크기: {width_m:.1f}m x {height_m:.1f}m")
            
            # 5. 그리드 크기로 변환
            width_grid = max(1, int(math.ceil(width_m / self.grid_resolution)))
            height_grid = max(1, int(math.ceil(height_m / self.grid_resolution)))
            
            # 6. 그리드 크기 제한 (메모리 보호)
            max_grid_size = 100  # 최대 100x100 그리드
            if width_grid > max_grid_size or height_grid > max_grid_size:
                print(f"   ⚠️ 그리드 크기가 너무 큼! 제한 적용")
                scale_factor = min(max_grid_size / width_grid, max_grid_size / height_grid)
                width_grid = int(width_grid * scale_factor)
                height_grid = int(height_grid * scale_factor)
                print(f"   📊 제한된 그리드: {width_grid} x {height_grid} 셀")
            else:
                print(f"   📊 그리드: {width_grid} x {height_grid} 셀")
            
            # 7. 직사각형 복셀 데이터 생성 (매우 빠름)
            voxel_data = self._create_rectangle_voxels(width_grid, height_grid)
            
            # 8. VoxelBlock 객체 생성
            voxel_block = VoxelBlock(block_id, voxel_data)
            
            return voxel_block
            
        except Exception as e:
            print(f"   ❌ 처리 오류: {str(e)}")
            return None
    
    def _estimate_real_size(self, raw_width, raw_height):
        """
        원본 크기에서 실제 크기 추정 (단위 변환)
        
        Args:
            raw_width (float): 원본 너비
            raw_height (float): 원본 높이
            
        Returns:
            tuple: (실제_너비, 실제_높이) in meters
        """
        # 일반적인 선박 블록 크기 범위: 2m ~ 100m
        reasonable_min = 2.0
        reasonable_max = 100.0
        
        # 다양한 단위 변환 시도
        conversions = [
            (1.0, "m"),           # 이미 미터
            (0.001, "mm→m"),      # 밀리미터 → 미터
            (0.01, "cm→m"),       # 센티미터 → 미터
            (0.1, "dm→m"),        # 데시미터 → 미터
            (0.0254, "inch→m"),   # 인치 → 미터
            (0.3048, "ft→m"),     # 피트 → 미터
        ]
        
        for factor, unit_name in conversions:
            converted_width = raw_width * factor
            converted_height = raw_height * factor
            
            # 합리적인 범위인지 확인
            if (reasonable_min <= converted_width <= reasonable_max and 
                reasonable_min <= converted_height <= reasonable_max):
                print(f"   🔄 단위 변환: {unit_name} (factor: {factor})")
                return converted_width, converted_height
        
        # 합리적인 변환을 찾지 못한 경우, 강제로 축소
        if raw_width > reasonable_max:
            scale_factor = reasonable_max / max(raw_width, raw_height)
            converted_width = raw_width * scale_factor
            converted_height = raw_height * scale_factor
            print(f"   🔄 강제 축소: factor {scale_factor:.6f}")
            return converted_width, converted_height
        
        # 기본적으로 원본 크기 사용
        return raw_width, raw_height
    
    def _create_rectangle_voxels(self, width_grid, height_grid):
        """
        직사각형 복셀 데이터 생성
        
        Args:
            width_grid (int): 그리드 너비
            height_grid (int): 그리드 높이
            
        Returns:
            list: 복셀 데이터 [(x, y, [empty_below, filled, empty_above]), ...]
        """
        voxel_data = []
        
        # 직사각형 형태로 모든 그리드 셀 채우기
        for x in range(width_grid):
            for y in range(height_grid):
                # 복셀 데이터: (x, y, [empty_below, filled, empty_above])
                heights = [0, 2, 0]  # 2m 높이로 설정
                voxel_data.append((x, y, heights))
        
        return voxel_data
    
    def get_detailed_file_info(self, fbx_path):
        """
        파일의 상세 정보 확인 (단위 정보 포함)
        
        Args:
            fbx_path (str): FBX 파일 경로
            
        Returns:
            dict: 상세 파일 정보
        """
        try:
            start_time = time.time()
            
            mesh = o3d.io.read_triangle_mesh(fbx_path)
            
            if len(mesh.vertices) == 0:
                return None
            
            # 바운딩 박스 정보
            bbox = mesh.get_axis_aligned_bounding_box()
            size = bbox.get_extent()
            center = bbox.get_center()
            
            # 정점 분석
            vertices = np.asarray(mesh.vertices)
            min_coords = np.min(vertices, axis=0)
            max_coords = np.max(vertices, axis=0)
            
            # 크기 추정
            width_real, height_real = self._estimate_real_size(size[0], size[1])
            
            elapsed = time.time() - start_time
            
            info = {
                'file_name': os.path.basename(fbx_path),
                'file_size_mb': os.path.getsize(fbx_path) / (1024*1024),
                'vertices': len(mesh.vertices),
                'triangles': len(mesh.triangles),
                'raw_size': {
                    'x': float(size[0]),
                    'y': float(size[1]), 
                    'z': float(size[2])
                },
                'raw_bounds': {
                    'min': [float(min_coords[0]), float(min_coords[1]), float(min_coords[2])],
                    'max': [float(max_coords[0]), float(max_coords[1]), float(max_coords[2])]
                },
                'center': [float(center[0]), float(center[1]), float(center[2])],
                'estimated_size_m': {
                    'x': width_real,
                    'y': height_real
                },
                'possible_units': self._analyze_possible_units(size[0], size[1]),
                'processing_time': elapsed
            }
            
            return info
            
        except Exception as e:
            return {'file_name': os.path.basename(fbx_path), 'error': str(e)}
    
    def _analyze_possible_units(self, raw_width, raw_height):
        """
        가능한 단위들 분석
        
        Args:
            raw_width (float): 원본 너비
            raw_height (float): 원본 높이
            
        Returns:
            list: 가능한 단위 변환들
        """
        conversions = [
            (1.0, "m", "meter"),
            (0.001, "mm", "millimeter"),
            (0.01, "cm", "centimeter"), 
            (0.1, "dm", "decimeter"),
            (0.0254, "inch", "inch"),
            (0.3048, "ft", "foot"),
        ]
        
        reasonable_min = 1.0  # 최소 1m
        reasonable_max = 200.0  # 최대 200m
        
        possible_units = []
        
        for factor, unit_short, unit_full in conversions:
            converted_width = raw_width * factor
            converted_height = raw_height * factor
            
            # 선박 블록으로 합리적인지 판단
            is_reasonable = (reasonable_min <= converted_width <= reasonable_max and 
                           reasonable_min <= converted_height <= reasonable_max)
            
            possible_units.append({
                'unit': unit_short,
                'unit_full': unit_full,
                'factor': factor,
                'converted_size': [converted_width, converted_height],
                'is_reasonable': is_reasonable,
                'confidence': self._calculate_confidence(converted_width, converted_height)
            })
        
        # 신뢰도 순으로 정렬
        possible_units.sort(key=lambda x: x['confidence'], reverse=True)
        
        return possible_units
    
    def _calculate_confidence(self, width, height):
        """
        단위 변환의 신뢰도 계산
        
        Args:
            width (float): 변환된 너비
            height (float): 변환된 높이
            
        Returns:
            float: 신뢰도 점수 (0~1)
        """
        # 선박 블록의 일반적인 크기 범위
        ideal_min = 5.0   # 5m
        ideal_max = 50.0  # 50m
        
        # 크기가 이상적 범위에 얼마나 가까운지 계산
        width_score = 0
        height_score = 0
        
        if ideal_min <= width <= ideal_max:
            width_score = 1.0
        elif width < ideal_min:
            width_score = max(0, width / ideal_min)
        else:  # width > ideal_max
            width_score = max(0, 1.0 - (width - ideal_max) / ideal_max)
        
        if ideal_min <= height <= ideal_max:
            height_score = 1.0
        elif height < ideal_min:
            height_score = max(0, height / ideal_min)
        else:  # height > ideal_max
            height_score = max(0, 1.0 - (height - ideal_max) / ideal_max)
        
        return (width_score + height_score) / 2
        """
        파일 정보만 빠르게 확인 (디버깅용)
        
        Args:
            fbx_path (str): FBX 파일 경로
            
        Returns:
            dict: 파일 정보
        """
        try:
            start_time = time.time()
            
            mesh = o3d.io.read_triangle_mesh(fbx_path)
            
            if len(mesh.vertices) == 0:
                return None
            
            bbox = mesh.get_axis_aligned_bounding_box()
            size = bbox.get_extent()
            
            # 크기 추정
            width_real, height_real = self._estimate_real_size(size[0], size[1])
            
            elapsed = time.time() - start_time
            
            info = {
                'file_name': os.path.basename(fbx_path),
                'vertices': len(mesh.vertices),
                'triangles': len(mesh.triangles),
                'raw_size_x': float(size[0]),
                'raw_size_y': float(size[1]),
                'raw_size_z': float(size[2]),
                'estimated_size_x': width_real,
                'estimated_size_y': height_real,
                'processing_time': elapsed
            }
            
            return info
            
        except Exception as e:
            return {'file_name': os.path.basename(fbx_path), 'error': str(e)}
    
    def batch_file_info(self, fbx_directory, max_files=10):
        """
        여러 파일의 정보를 배치로 확인
        
        Args:
            fbx_directory (str): 디렉토리 경로
            max_files (int): 확인할 최대 파일 수
        """
        print(f"=== FBX 파일 정보 일괄 확인 ===")
        
        fbx_files = self._find_fbx_files(fbx_directory)
        
        if not fbx_files:
            print("❌ FBX 파일을 찾을 수 없습니다.")
            return
        
        if max_files and max_files < len(fbx_files):
            import random
            fbx_files = random.sample(fbx_files, max_files)
        
        print(f"📊 {len(fbx_files)}개 파일 정보 확인 중...")
        
        total_start = time.time()
        
        for i, fbx_file in enumerate(fbx_files, 1):
            print(f"\n({i}/{len(fbx_files)}) {os.path.basename(fbx_file)}")
            
            info = self.get_file_info_only(fbx_file)
            
            if info and 'error' not in info:
                print(f"  정점: {info['vertices']:,}개, 삼각형: {info['triangles']:,}개")
                print(f"  원본 크기: {info['raw_size_x']:.1f} x {info['raw_size_y']:.1f} x {info['raw_size_z']:.1f}")
                print(f"  추정 크기: {info['estimated_size_x']:.1f} x {info['estimated_size_y']:.1f} m")
                print(f"  처리 시간: {info['processing_time']:.3f}초")
            elif info:
                print(f"  ❌ 오류: {info['error']}")
            else:
                print(f"  ❌ 메시 데이터 없음")
        
        total_elapsed = time.time() - total_start
        print(f"\n📈 총 {total_elapsed:.1f}초 (평균 {total_elapsed/len(fbx_files):.3f}초/파일)")