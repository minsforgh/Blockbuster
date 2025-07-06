#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1m 해상도 자항선 블록 배치 시스템 (원본 알고리즘 완전 호환)
- 84m × 36m 자항선 (84 × 36 그리드)
- 선미 5m 여유, 블록간 1m 여유
- 크레인/트레슬 블록 분류
- CSV 및 JSON 파일 지원
- 원본 BacktrackingPlacer 완전 호환
"""

import json
import sys
import os
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')

# 영어 폰트 설정 (한글 깨짐 방지)
plt.rcParams['font.family'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 프로젝트 모듈 import 시도
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from models.voxel_block import VoxelBlock
    from models.placement_area import PlacementArea
    from algorithms.backtracking_placer import BacktrackingPlacer
    ORIGINAL_ALGORITHM_AVAILABLE = True
    print(f"[INFO] Original algorithm modules loaded successfully")
except ImportError as e:
    print(f"[INFO] Original algorithm modules not found, using simple placement algorithm")
    ORIGINAL_ALGORITHM_AVAILABLE = False

class ShipPlacementArea(PlacementArea):
    """원본 PlacementArea를 상속받은 자항선 특화 배치 영역"""
    
    def __init__(self, width=84, height=36, grid_resolution=1.0):
        """
        Args:
            width (int): 자항선 너비 그리드 수
            height (int): 자항선 높이 그리드 수
            grid_resolution (float): 그리드 해상도 (m)
        """
        super().__init__(width, height)
        self.grid_resolution = grid_resolution
        self.actual_width = width * grid_resolution
        self.actual_height = height * grid_resolution
        
        # 자항선 제약조건 (그리드 단위)
        self.bow_clearance = int(5.0 / grid_resolution)  # 선미 5m
        self.block_spacing = int(1.0 / grid_resolution)  # 블록간 1m
        
        print(f"Ship Placement Area Initialized:")
        print(f"   Size: {self.actual_width}m × {self.actual_height}m ({width} × {height} grids)")
        print(f"   Grid resolution: {grid_resolution}m")
        print(f"   Bow clearance: {self.bow_clearance} grids ({self.bow_clearance * grid_resolution}m)")
        print(f"   Block spacing: {self.block_spacing} grids ({self.block_spacing * grid_resolution}m)")
    
    def can_place_block(self, block, pos_x, pos_y):
        """자항선 제약조건을 고려한 블록 배치 가능 여부 확인"""
        # 1. 기본 배치 가능성 확인 (원본 알고리즘)
        if not super().can_place_block(block, pos_x, pos_y):
            return False
        
        # 2. 선미(오른쪽) 여백 확인
        block_right_edge = pos_x + block.width
        if block_right_edge > self.width - self.bow_clearance:
            return False
        
        # 3. 다른 블록과의 간격 확인
        footprint = block.get_footprint()
        
        for vx, vy in footprint:
            grid_x = pos_x + vx - block.min_x
            grid_y = pos_y + vy - block.min_y
            
            # 주변 간격 확인 (spacing 범위 내 다른 블록 있는지)
            for dx in range(-self.block_spacing, self.block_spacing + 1):
                for dy in range(-self.block_spacing, self.block_spacing + 1):
                    if dx == 0 and dy == 0:
                        continue
                    
                    check_x = grid_x + dx
                    check_y = grid_y + dy
                    
                    # 배치 영역 내에 있고 다른 블록이 있는 경우
                    if (0 <= check_x < self.width and 
                        0 <= check_y < self.height and
                        self.grid[check_y, check_x] is not None):
                        return False
        
        return True

class SimpleBlock:
    """간단한 블록 클래스 (원본 VoxelBlock 인터페이스 호환)"""
    
    def __init__(self, block_id, width, height, block_type="unknown"):
        self.id = block_id
        self.block_id = block_id
        self.width = width
        self.height = height
        self.block_type = block_type
        self.rotation = 0
        self.position = None
        
        # VoxelBlock 호환을 위한 속성들
        self.min_x = 0
        self.min_y = 0
        self.max_x = width - 1
        self.max_y = height - 1
    
    def get_footprint(self):
        """블록의 발자국 반환 (VoxelBlock 호환)"""
        footprint = []
        for x in range(self.width):
            for y in range(self.height):
                footprint.append((x, y))
        return footprint
    
    def get_area(self):
        """블록 면적 반환"""
        return self.width * self.height
    
    def rotate(self):
        """블록 회전 (90도)"""
        self.width, self.height = self.height, self.width
        self.rotation = (self.rotation + 90) % 360
        self.max_x = self.width - 1
        self.max_y = self.height - 1

class GreedyPlacer:
    """간단한 그리디 배치 알고리즘 (원본 알고리즘 없을 때 사용)"""
    
    def __init__(self, area, blocks, max_time=60):
        self.area = area
        self.blocks = blocks
        self.max_time = max_time
        self.start_time = None
    
    def optimize(self):
        """그리디 배치 실행"""
        self.start_time = time.time()
        
        # 블록을 면적 순으로 정렬 (큰 것부터)
        sorted_blocks = sorted(self.blocks, 
                             key=lambda b: b.get_area(), 
                             reverse=True)
        
        # area에 블록들 추가
        for block in sorted_blocks:
            self.area.unplaced_blocks[block.id] = block
        
        placed_count = 0
        for block in sorted_blocks:
            # 시간 제한 확인
            if time.time() - self.start_time > self.max_time:
                break
            
            # 가능한 위치 탐색 (왼쪽 위부터)
            placed = False
            for y in range(self.area.height - block.height + 1):
                for x in range(self.area.width - block.width + 1):
                    if self.area.can_place_block(block, x, y):
                        if self.area.place_block(block, x, y):
                            placed_count += 1
                            placed = True
                            break
                if placed:
                    break
        
        return self.area

class ShipPlacer1M:
    """1m 해상도 자항선 배치 시스템"""
    
    def __init__(self, ship_width=84, ship_height=36, grid_resolution=1.0):
        self.ship_width = ship_width
        self.ship_height = ship_height
        self.grid_resolution = grid_resolution
        
        print(f"1M Resolution Ship Placement System Initialized")
        print(f"   Ship: {ship_width}m × {ship_height}m")
        print(f"   Resolution: {grid_resolution}m/grid")
        print(f"   Grid: {int(ship_width/grid_resolution)} × {int(ship_height/grid_resolution)}")
    
    def load_blocks_from_csv(self, csv_path, max_blocks=None):
        """CSV 파일에서 블록 로드"""
        print(f"Loading blocks from CSV: {csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        print(f"   Found {len(df)} blocks in CSV")
        
        if max_blocks:
            df = df.head(max_blocks)
            print(f"   Using first {max_blocks} blocks only")
        
        blocks = []
        for _, row in df.iterrows():
            if ORIGINAL_ALGORITHM_AVAILABLE:
                # VoxelBlock 생성 (원본 알고리즘용)
                width = int(row['grid_width'])
                height = int(row['grid_height'])
                
                voxel_data = []
                for x in range(width):
                    for y in range(height):
                        voxel_data.append((x, y, [0, 1, 0]))
                
                block = VoxelBlock(row['block_id'], voxel_data)
                block.block_type = row.get('block_type', 'unknown')
            else:
                # SimpleBlock 생성 (간단 알고리즘용)
                block = SimpleBlock(
                    block_id=row['block_id'],
                    width=int(row['grid_width']),
                    height=int(row['grid_height']),
                    block_type=row.get('block_type', 'unknown')
                )
            
            blocks.append(block)
        
        # 통계 출력
        type_counts = defaultdict(int)
        for block in blocks:
            type_counts[block.block_type] += 1
        
        print(f"   Successfully loaded {len(blocks)} blocks")
        print(f"   Block types:")
        for block_type, count in type_counts.items():
            print(f"      {block_type}: {count}")
        
        return blocks
    
    def load_blocks_from_json(self, json_path, max_blocks=None):
        """JSON 파일에서 블록 로드"""
        print(f"Loading blocks from JSON: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        blocks_data = data.get('blocks', [])
        if max_blocks:
            blocks_data = blocks_data[:max_blocks]
            print(f"Using first {max_blocks} blocks only")
        
        print(f"   Found {len(blocks_data)} blocks in JSON")
        
        blocks = []
        for block_info in blocks_data:
            if ORIGINAL_ALGORITHM_AVAILABLE:
                # VoxelBlock 사용
                voxel_data = []
                width = block_info['grid_size_2d']['width']
                height = block_info['grid_size_2d']['height']
                
                for x in range(width):
                    for y in range(height):
                        voxel_data.append((x, y, [0, 1, 0]))
                
                block = VoxelBlock(block_info['block_id'], voxel_data)
                block.block_type = block_info.get('block_type', 'unknown')
            else:
                # SimpleBlock 사용
                block = SimpleBlock(
                    block_id=block_info['block_id'],
                    width=block_info['grid_size_2d']['width'],
                    height=block_info['grid_size_2d']['height'],
                    block_type=block_info.get('block_type', 'unknown')
                )
            
            blocks.append(block)
        
        # 통계 출력
        type_counts = defaultdict(int)
        for block in blocks:
            type_counts[block.block_type] += 1
        
        print(f"   Successfully loaded {len(blocks)} blocks")
        print(f"   Block types:")
        for block_type, count in type_counts.items():
            print(f"      {block_type}: {count}")
        
        return blocks
    
    def place_blocks(self, blocks, max_time=60):
        """블록 배치 실행"""
        print(f"Block placement started...")
        print(f"   Blocks to place: {len(blocks)}")
        print(f"   Max time: {max_time} seconds")
        print("="*80)
        
        # 자항선 특화 배치 영역 생성
        area = ShipPlacementArea(
            width=int(self.ship_width/self.grid_resolution),
            height=int(self.ship_height/self.grid_resolution),
            grid_resolution=self.grid_resolution
        )
        
        if ORIGINAL_ALGORITHM_AVAILABLE:
            print(f"Using original algorithm (heuristic backtracking)")
            try:
                placer = BacktrackingPlacer(area, blocks, max_time)
                result = placer.optimize()
                return result
                
            except Exception as e:
                print(f"Original algorithm failed: {e}")
                print(f"Switching to simple algorithm")
        
        print(f"Using simple greedy algorithm")
        placer = GreedyPlacer(area, blocks, max_time)
        result = placer.optimize()
        
        return result
    
    def visualize(self, result, save_path=None, show=True):
        """배치 결과 시각화"""
        print(f"Generating placement result visualization...")
        
        # 영어 폰트 재설정
        plt.rcParams['font.family'] = ['DejaVu Sans']
        
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))
        
        # 자항선 경계 그리기
        ship_rect = patches.Rectangle(
            (0, 0), result.width, result.height,
            linewidth=3, edgecolor='navy', facecolor='lightblue', alpha=0.3
        )
        ax.add_patch(ship_rect)
        
        # 선미 여유 영역 표시
        bow_rect = patches.Rectangle(
            (result.width - result.bow_clearance, 0), 
            result.bow_clearance, result.height,
            linewidth=2, edgecolor='red', facecolor='red', alpha=0.2
        )
        ax.add_patch(bow_rect)
        
        # 배치된 블록들 그리기
        colors = {'crane': 'orange', 'trestle': 'green', 'unknown': 'gray'}
        
        # 원본 알고리즘: placed_blocks는 딕셔너리
        if hasattr(result.placed_blocks, 'values'):
            placed_blocks_list = list(result.placed_blocks.values())
        else:
            placed_blocks_list = result.placed_blocks
        
        for block in placed_blocks_list:
            if hasattr(block, 'position') and block.position is not None:
                pos_x, pos_y = block.position
                color = colors.get(block.block_type, 'gray')
                
                # 블록 사각형
                block_rect = patches.Rectangle(
                    (pos_x, pos_y), block.width, block.height,
                    linewidth=1, edgecolor='black', facecolor=color, alpha=0.7
                )
                ax.add_patch(block_rect)
                
                # 블록 ID 텍스트
                center_x = pos_x + block.width / 2
                center_y = pos_y + block.height / 2
                block_id_text = block.id if hasattr(block, 'id') else block.block_id
                ax.text(center_x, center_y, block_id_text, 
                       ha='center', va='center', fontsize=8, 
                       color='white', weight='bold')
        
        # 축 설정
        ax.set_xlim(-2, result.width + 2)
        ax.set_ylim(-2, result.height + 2)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('X Direction (m)', fontsize=12)
        ax.set_ylabel('Y Direction (m)', fontsize=12)
        
        # 제목과 통계
        total_blocks = len(result.placed_blocks) + len(result.unplaced_blocks)
        placed_count = len(result.placed_blocks)
        success_rate = (placed_count / total_blocks) * 100 if total_blocks > 0 else 0
        
        crane_blocks = [b for b in placed_blocks_list if getattr(b, 'block_type', 'unknown') == 'crane']
        trestle_blocks = [b for b in placed_blocks_list if getattr(b, 'block_type', 'unknown') == 'trestle']
        
        # 공간 활용률 계산
        total_area = result.width * result.height
        used_area = sum(block.get_area() for block in placed_blocks_list)
        space_utilization = (used_area / total_area) * 100
        
        plt.title(f'Ship Block Placement Result (1m Resolution)\n'
                 f'Placed: {placed_count}/{total_blocks} ({success_rate:.1f}%) | '
                 f'Crane: {len(crane_blocks)} | Trestle: {len(trestle_blocks)} | '
                 f'Space Usage: {space_utilization:.1f}%',
                 fontsize=14, pad=20)
        
        # 범례
        legend_elements = [
            patches.Patch(color='orange', alpha=0.7, label='Crane Blocks'),
            patches.Patch(color='green', alpha=0.7, label='Trestle Blocks'),
            patches.Patch(color='red', alpha=0.2, label='Bow Clearance (5m)'),
            patches.Patch(color='lightblue', alpha=0.3, label='Ship Area')
        ]
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
        
        # 상세 통계 텍스트
        stats_text = f"""Placement Statistics:
   Total blocks: {total_blocks}
   Placed: {placed_count}
   Unplaced: {len(result.unplaced_blocks)}
   Success rate: {success_rate:.1f}%

Block Types:
   Crane: {len(crane_blocks)}
   Trestle: {len(trestle_blocks)}

Space Utilization:
   Used area: {used_area:,} cells
   Total area: {total_area:,} cells
   Utilization: {space_utilization:.1f}%

Constraints:
   Block spacing: {result.block_spacing * result.grid_resolution}m
   Bow clearance: {result.bow_clearance * result.grid_resolution}m
"""
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=10, va='top', ha='left', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))
        
        plt.tight_layout()
        
        # 저장
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   Visualization saved: {save_path}")
        
        # 표시
        if show:
            plt.show()
        
        return fig

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("🚢" + "="*70)
        print("1M Resolution Ship Block Placement System")
        print("🚢" + "="*70)
        print("")
        print("Usage:")
        print("  python ship_placer_1m.py <file.csv|file.json>")
        print("  python ship_placer_1m.py <file.csv|file.json> <max_blocks>")
        print("  python ship_placer_1m.py <file.csv|file.json> <max_blocks> <max_time>")
        print("")
        print("Examples:")
        print("  python ship_placer_1m.py blocks_summary.csv")
        print("  python ship_placer_1m.py block_processing_results.json 20")
        print("  python ship_placer_1m.py blocks_summary.csv 15 120")
        print("")
        print("Features:")
        print("  Ship size: 84m × 36m (84 × 36 grid)")
        print("  Constraints: 1m block spacing, 5m bow clearance")
        print("  CSV/JSON file support")
        print("  Real-time visualization")
        print("  Original/Simple algorithm auto-selection")
        return
    
    # 인수 파싱
    file_path = sys.argv[1]
    max_blocks = int(sys.argv[2]) if len(sys.argv) > 2 else None
    max_time = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    try:
        print("🚢" + "="*70)
        print("1M Resolution Ship Block Placement System")
        print("🚢" + "="*70)
        
        # 배치 시스템 생성
        placer = ShipPlacer1M(ship_width=84, ship_height=36, grid_resolution=1.0)
        
        # 파일 확장자에 따라 로드 방법 선택
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.csv':
            blocks = placer.load_blocks_from_csv(file_path, max_blocks)
        elif file_ext == '.json':
            blocks = placer.load_blocks_from_json(file_path, max_blocks)
        else:
            print(f"❌ Unsupported file format: {file_ext}")
            print(f"   Supported formats: .csv, .json")
            return
        
        if not blocks:
            print("❌ No blocks loaded")
            return
        
        # 배치 실행
        result = placer.place_blocks(blocks, max_time)
        
        if result:
            # 시각화
            output_dir = Path(file_path).parent
            save_filename = f"ship_placement_1m_{Path(file_path).stem}.png"
            viz_path = output_dir / save_filename
            
            placer.visualize(result, save_path=viz_path, show=True)
            
            print(f"\n🎉 === 1M Resolution Placement Complete! ===")
            print(f"Placed blocks: {len(result.placed_blocks)}/{len(result.placed_blocks) + len(result.unplaced_blocks)}")
            print(f"Success rate: {len(result.placed_blocks)/(len(result.placed_blocks) + len(result.unplaced_blocks))*100:.1f}%")
            print(f"Result saved: {viz_path}")
        else:
            print("❌ Placement failed")
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()