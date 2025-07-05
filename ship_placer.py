"""
자항선 블록 배치 시스템 (수정된 원본 알고리즘 사용)
ship_placer_original_y_first.py - 기존 프로젝트 알고리즘을 Y축 우선으로 수정하여 사용
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import sys
import os
import json
import time
import copy
from pathlib import Path
from collections import defaultdict
import warnings

# 한글 폰트 설정
def setup_korean_font():
    """한글 폰트 자동 설정"""
    try:
        import platform
        import matplotlib.font_manager as fm
        
        system = platform.system()
        
        if system == "Windows":
            korean_fonts = ["Malgun Gothic", "맑은 고딕", "Gulim", "굴림"]
        elif system == "Darwin":  # macOS
            korean_fonts = ["AppleGothic", "Apple SD Gothic Neo", "Nanum Gothic"]
        else:  # Linux
            korean_fonts = ["Nanum Gothic", "나눔고딕", "UnDotum"]
        
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font in korean_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                plt.rcParams['axes.unicode_minus'] = False
                print(f"[INFO] Korean font set: {font}")
                return True
        
        print(f"[WARNING] No Korean font found, using fallback text")
        return False
        
    except Exception:
        print(f"[WARNING] Font setup failed, using fallback text")
        return False

# 폰트 경고 억제
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
warnings.filterwarnings('ignore', message='.*missing from font.*')
warnings.filterwarnings('ignore', message='.*Glyph.*missing.*')

# 한글 폰트 설정 시도
KOREAN_FONT_AVAILABLE = setup_korean_font()

# 프로젝트 모듈 import (수정된 원본 알고리즘 사용)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from models.voxel_block import VoxelBlock
    from models.placement_area import PlacementArea
    # 수정된 원본 알고리즘 import
    from algorithms.backtracking_placer import BacktrackingPlacer
    from algorithms.candidate_generator import CandidateGenerator
    print(f"[INFO] Modified original project modules loaded successfully")
    ORIGINAL_ALGORITHM_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Cannot find project modules: {e}")
    print(f"[INFO] Falling back to basic placement algorithm")
    ORIGINAL_ALGORITHM_AVAILABLE = False

class ShipPlacementArea(PlacementArea):
    """자항선 특화 배치 영역 클래스 (원본 PlacementArea 확장)"""
    
    def __init__(self, width=42, height=18, grid_resolution=2.0):
        """
        Args:
            width (int): 자항선 너비 그리드 수 (84m / 2m = 42)
            height (int): 자항선 높이 그리드 수 (36m / 2m = 18)
            grid_resolution (float): 그리드 해상도 (m)
        """
        super().__init__(width, height)
        self.grid_resolution = grid_resolution
        self.actual_width = width * grid_resolution  # 84m
        self.actual_height = height * grid_resolution  # 36m
        
        # 자항선 제약조건 (그리드 단위)
        self.bow_clearance = int(5.0 / grid_resolution)  # 선수 5m
        self.block_spacing = max(1, int(1.0 / grid_resolution))  # 블록 간격 1m
        
        print(f"🚢 Ship Placement Area initialized (Original Algorithm Y-first):")
        print(f"   📏 Size: {self.actual_width}m × {self.actual_height}m ({width} × {height} grids)")
        print(f"   🎯 Grid resolution: {grid_resolution}m")
        print(f"   ⛵ Bow clearance: {self.bow_clearance} grids ({self.bow_clearance * grid_resolution}m)")
        print(f"   📐 Block spacing: {self.block_spacing} grids ({self.block_spacing * grid_resolution}m)")
        print(f"   🔄 Fill order: Y-axis first (modified original algorithm)")
    
    def can_place_block(self, block, pos_x, pos_y):
        """
        자항선 제약조건을 고려한 블록 배치 가능 여부 확인
        원본 can_place_block을 오버라이드하여 자항선 제약조건 추가
        """
        # 1. 기본 배치 가능성 확인 (원본 알고리즘)
        if not super().can_place_block(block, pos_x, pos_y):
            return False
        
        # 2. 선수(오른쪽) 여백 확인
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

class ShipPlacer:
    """자항선 블록 배치 클래스 (수정된 원본 알고리즘 사용)"""
    
    def __init__(self, ship_width=84, ship_height=36, grid_resolution=2.0):
        self.ship_width = ship_width
        self.ship_height = ship_height
        self.grid_resolution = grid_resolution
        self.grid_width = int(ship_width / grid_resolution)
        self.grid_height = int(ship_height / grid_resolution)
        
        print(f"🚢 Ship Placer initialized (Modified Original Algorithm):")
        print(f"   📏 Ship size: {ship_width}m × {ship_height}m")
        print(f"   📐 Grid size: {self.grid_width} × {self.grid_height}")
        print(f"   🎯 Resolution: {grid_resolution}m per grid")
        print(f"   🔄 Fill order: Y-axis first (modified from original)")
        
        if ORIGINAL_ALGORITHM_AVAILABLE:
            print(f"   🧠 Algorithm: Modified Original (Y-first Heuristic Backtracking)")
        else:
            print(f"   🧠 Algorithm: Fallback (Simple Greedy)")
    
    def load_blocks(self, json_path, max_blocks=None):
        """JSON에서 블록 로드"""
        print(f"\n📁 Loading blocks from: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        blocks_data = data.get('blocks', [])
        if max_blocks:
            blocks_data = blocks_data[:max_blocks]
            print(f"🔢 Using first {max_blocks} blocks for testing")
        
        print(f"   📦 Found {len(blocks_data)} blocks to process")
        
        blocks = []
        for block_info in blocks_data:
            block_id = block_info['block_id']
            grid_width = block_info['grid_size_2d']['width']
            grid_height = block_info['grid_size_2d']['height']
            
            # 2D 직사각형 복셀 데이터 생성
            voxel_data = []
            for x in range(grid_width):
                for y in range(grid_height):
                    voxel_data.append((x, y, [0, 1, 0]))
            
            # VoxelBlock 생성
            block = VoxelBlock(block_id, voxel_data)
            block.block_type = block_info.get('block_type', 'unknown')
            block.original_info = block_info
            blocks.append(block)
        
        # 블록 유형별 통계
        type_counts = defaultdict(int)
        for block in blocks:
            type_counts[block.block_type] += 1
        
        print(f"   ✅ Successfully loaded {len(blocks)} blocks")
        print(f"   📊 Block types:")
        for block_type, count in type_counts.items():
            print(f"      {block_type}: {count}")
        
        return blocks
    
    def place_blocks(self, blocks, max_time=60):
        """블록 배치 실행 (수정된 원본 알고리즘 사용)"""
        print(f"\n🚀 Starting ship block placement with modified original algorithm...")
        print(f"   📦 Blocks to place: {len(blocks)}")
        print("="*70)
        
        # 자항선 특화 배치 영역 생성
        ship_area = ShipPlacementArea(
            width=self.grid_width,
            height=self.grid_height,
            grid_resolution=self.grid_resolution
        )
        
        if ORIGINAL_ALGORITHM_AVAILABLE:
            # 수정된 원본 백트래킹 알고리즘 사용
            print(f"🧠 Using MODIFIED ORIGINAL algorithm (Y-first Heuristic Backtracking)")
            print(f"   📋 Original algorithm features:")
            print(f"      - Heuristic Backtracking")
            print(f"      - Bin Packing strategies (Top-Left, Adjacent, Boundary)")
            print(f"      - 6 heuristic criteria scoring")
            print(f"   🔧 Modifications:")
            print(f"      - X-axis priority → Y-axis priority")
            print(f"      - Width-based sorting → Height-based sorting")
            print(f"      - Left alignment → Top alignment")
            print(f"      - Ship constraints integration")
            
            placer = BacktrackingPlacer(ship_area, blocks, max_time)
            result = placer.optimize()
            
            return result
            
        else:
            # 폴백: 간단한 그리디 알고리즘
            print(f"🧠 Using fallback algorithm (Simple Greedy)")
            print(f"   ℹ️ Reason: Original algorithm modules not available")
            
            return self._fallback_greedy_placement(ship_area, blocks)
    
    def _fallback_greedy_placement(self, ship_area, blocks):
        """폴백 그리디 배치 알고리즘"""
        ship_area.add_blocks(blocks)
        
        # 블록 정렬 (Y축 우선에 맞게 높이 우선)
        sorted_blocks = sorted(blocks, key=lambda b: (-b.height, -b.get_area()))
        
        placed_count = 0
        start_time = time.time()
        
        for i, block in enumerate(sorted_blocks, 1):
            print(f"   📦 [{i:3d}/{len(sorted_blocks)}] Placing {block.id[:15]:15}")
            
            placed = False
            
            # Y축 우선으로 가능한 모든 위치에서 배치 시도 (X축 먼저, Y축 나중)
            for x in range(ship_area.width - block.width):
                for y in range(ship_area.height - block.height):
                    
                    if ship_area.can_place_block(block, x, y):
                        if ship_area.place_block(block, x, y):
                            print(f"      ✅ Placed at ({x}, {y})")
                            placed_count += 1
                            placed = True
                            break
                
                if placed:
                    break
            
            if not placed:
                print(f"      ❌ Could not place")
        
        elapsed_time = time.time() - start_time
        
        print(f"\n🎉 Fallback greedy placement complete!")
        print(f"   ⏱️ Time: {elapsed_time:.1f}s")
        print(f"   📦 Placed: {len(ship_area.placed_blocks)}/{len(blocks)} blocks")
        print(f"   📊 Success rate: {len(ship_area.placed_blocks)/len(blocks)*100:.1f}%")
        print(f"   🎯 Space utilization: {ship_area.get_placement_score():.3f}")
        
        return ship_area
    
    def visualize(self, ship_area, save_path=None, show=True):
        """시각화"""
        print(f"\n🎨 Creating visualization...")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # 왼쪽: 배치 결과
        self._draw_layout(ax1, ship_area)
        
        # 오른쪽: 통계
        self._draw_stats(ax2, ship_area)
        
        algorithm_name = "Modified Original (Y-first)" if ORIGINAL_ALGORITHM_AVAILABLE else "Fallback Greedy"
        plt.suptitle(f'🚢 Ship Block Placement Result ({algorithm_name})', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def _draw_layout(self, ax, ship_area):
        """레이아웃 그리기"""
        ax.set_xlim(0, ship_area.width)
        ax.set_ylim(0, ship_area.height)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        
        # 선수 여백 표시
        bow_x = ship_area.width - ship_area.bow_clearance
        bow_rect = patches.Rectangle(
            (bow_x, 0), ship_area.bow_clearance, ship_area.height,
            facecolor='red', alpha=0.2, edgecolor='red', linewidth=2
        )
        ax.add_patch(bow_rect)
        ax.text(bow_x + ship_area.bow_clearance/2, ship_area.height/2, 
               'BOW\n(5m)', ha='center', va='center', fontsize=10, 
               color='red', fontweight='bold')
        
        # 배치된 블록들
        colors = plt.cm.Set3(np.linspace(0, 1, len(ship_area.placed_blocks)))
        
        for i, (block_id, block) in enumerate(ship_area.placed_blocks.items()):
            footprint = block.get_positioned_footprint()
            color = colors[i % len(colors)]
            
            for x, y in footprint:
                rect = patches.Rectangle(
                    (x, y), 1, 1,
                    facecolor=color, alpha=0.7,
                    edgecolor='black', linewidth=1
                )
                ax.add_patch(rect)
            
            # 블록 ID 표시
            if footprint:
                center_x = sum(x for x, y in footprint) / len(footprint)
                center_y = sum(y for x, y in footprint) / len(footprint)
                
                type_symbol = "🔧" if getattr(block, 'block_type', 'unknown') == 'crane' else "🚚"
                ax.text(center_x + 0.5, center_y + 0.5, f"{type_symbol}\n{block_id[:8]}",
                       ha='center', va='center', fontsize=8, fontweight='bold')
        
        algorithm_name = "Modified Original (Y-first)" if ORIGINAL_ALGORITHM_AVAILABLE else "Fallback Greedy"
        ax.set_title(f'Ship Layout - {algorithm_name}')
        ax.set_xlabel('X (Grid)')
        ax.set_ylabel('Y (Grid)')
    
    def _draw_stats(self, ax, ship_area):
        """통계 그리기"""
        ax.axis('off')
        
        total_blocks = len(ship_area.placed_blocks) + len(ship_area.unplaced_blocks)
        placed_blocks = len(ship_area.placed_blocks)
        success_rate = (placed_blocks / total_blocks * 100) if total_blocks > 0 else 0
        
        placed_area = sum(block.get_area() for block in ship_area.placed_blocks.values())
        total_area = ship_area.width * ship_area.height
        space_utilization = (placed_area / total_area * 100)
        
        crane_blocks = [b for b in ship_area.placed_blocks.values() 
                       if hasattr(b, 'block_type') and b.block_type == 'crane']
        trestle_blocks = [b for b in ship_area.placed_blocks.values() 
                         if hasattr(b, 'block_type') and b.block_type == 'trestle']
        
        algorithm_name = "Modified Original (Y-first)" if ORIGINAL_ALGORITHM_AVAILABLE else "Fallback Greedy"
        
        stats_text = f"""
📊 PLACEMENT STATISTICS (MODIFIED ORIGINAL)

🧠 Algorithm: {algorithm_name}
🔄 Fill Order: Y-axis first (modified from original X-axis first)

🚢 Ship Info:
   Size: {self.ship_width}m × {self.ship_height}m
   Grid: {ship_area.width} × {ship_area.height}
   Resolution: {self.grid_resolution}m/grid

📦 Block Placement:
   Total blocks: {total_blocks}
   Placed: {placed_blocks}
   Unplaced: {len(ship_area.unplaced_blocks)}
   Success rate: {success_rate:.1f}%

🏗️ Block Types:
   🔧 Crane: {len(crane_blocks)}
   🚚 Trestle: {len(trestle_blocks)}

📐 Space Utilization:
   Used area: {placed_area:,} cells
   Total area: {total_area:,} cells
   Utilization: {space_utilization:.1f}%

⚠️ Constraints Applied:
   ✅ Block spacing: {ship_area.block_spacing * self.grid_resolution}m
   ✅ Bow clearance: {ship_area.bow_clearance * self.grid_resolution}m

🔧 Original Algorithm Modifications:
   ✅ Height-based block sorting (was width-based)
   ✅ Y-axis priority scoring (was X-axis priority)
   ✅ Top alignment preference (was left alignment)
   ✅ Ship constraint integration
"""
        
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes, 
               fontsize=9, va='top', ha='left', fontfamily='monospace',
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightyellow", alpha=0.8))

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("🚢" + "="*70)
        print("SHIP BLOCK PLACEMENT SYSTEM (MODIFIED ORIGINAL)")
        print("🚢" + "="*70)
        print("")
        print("사용법:")
        print("  python ship_placer_original_y_first.py <processed_blocks.json>")
        print("  python ship_placer_original_y_first.py <processed_blocks.json> <max_blocks>")
        print("  python ship_placer_original_y_first.py <processed_blocks.json> <max_blocks> <max_time>")
        print("")
        print("예시:")
        print("  python ship_placer_original_y_first.py 2d_blocks_output/block_processing_results.json")
        print("  python ship_placer_original_y_first.py results.json 10")
        print("  python ship_placer_original_y_first.py results.json 20 120")
        print("")
        print("✨ 특징 (MODIFIED ORIGINAL):")
        print("  🚢 자항선 크기: 84m × 36m")
        print("  📐 제약조건: 블록 간격 1m, 선수 여백 5m")
        print("  🧠 알고리즘: 기존 프로젝트 알고리즘을 Y축 우선으로 수정")
        print("  🎯 원본 Bin Packing 전략 유지 (Top-Left, Adjacent, Boundary)")
        print("  📊 원본 6가지 휴리스틱 기준 유지 (가중치 조정)")
        print("")
        print("🔧 원본 알고리즘에서 수정된 부분:")
        print("  - algorithms/candidate_generator.py:")
        print("    • 탐색 순서: Y축 먼저 X축 나중 → X축 먼저 Y축 나중")
        print("    • 점수 계산: X축 우선 → Y축 우선")
        print("    • 정렬 방향: 왼쪽 정렬 → 위쪽 정렬")
        print("  - algorithms/backtracking_placer.py:")
        print("    • 블록 정렬: 너비 우선 → 높이 우선")
        print("  - models/placement_area.py:")
        print("    • 자항선 제약조건 추가 (선수 여백, 블록 간격)")
        print("")
        print("⚠️ 참고:")
        print("  - 수정된 원본 알고리즘 파일들이 필요합니다")
        print("  - 원본 알고리즘 없을 시 간단한 그리디 알고리즘 사용")
        return
    
    json_path = sys.argv[1]
    max_blocks = int(sys.argv[2]) if len(sys.argv) > 2 else None
    max_time = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    try:
        print("🚢" + "="*70)
        print("SHIP BLOCK PLACEMENT SYSTEM (MODIFIED ORIGINAL)")
        print("🚢" + "="*70)
        
        if ORIGINAL_ALGORITHM_AVAILABLE:
            print("✅ Modified original project algorithm modules available")
            print("🧠 Will use: Modified Original (Y-first Heuristic Backtracking)")
            print("🔧 Modifications: Y-axis priority, Height-based sorting, Top alignment")
        else:
            print("⚠️ Original project algorithm modules not found")
            print("🧠 Will use: Simple Greedy (fallback)")
        
        # 배치 시스템 생성
        placer = ShipPlacer(ship_width=84, ship_height=36, grid_resolution=2.0)
        
        # 블록 로드
        blocks = placer.load_blocks(json_path, max_blocks)
        
        if not blocks:
            print("❌ No blocks loaded")
            return
        
        # 배치 실행
        result = placer.place_blocks(blocks, max_time)
        
        # 결과 확인
        print(f"\n🔍 Final result check:")
        print(f"   result object exists: {result is not None}")
        if result:
            print(f"   placed_blocks count: {len(result.placed_blocks)}")
            print(f"   unplaced_blocks count: {len(result.unplaced_blocks)}")
        
        # 시각화
        if result and len(result.placed_blocks) > 0:
            output_dir = Path(json_path).parent
            viz_path = output_dir / "ship_placement_result_modified_original.png"
            
            placer.visualize(result, save_path=viz_path, show=True)
            
            print(f"\n🎉 === MODIFIED ORIGINAL PLACEMENT COMPLETE! ===")
            print(f"✅ Placed {len(result.placed_blocks)} blocks successfully")
            print(f"📊 Space utilization: {result.get_placement_score():.1%}")
            print(f"🎨 Visualization saved: {viz_path}")
            print(f"🔄 Fill order: Y-axis first (modified from original)")
            
            if ORIGINAL_ALGORITHM_AVAILABLE:
                print(f"🧠 Algorithm used: Modified Original Project (Y-first Heuristic Backtracking)")
                print(f"🔧 Key modifications:")
                print(f"   - Height-based block sorting (was width-based)")
                print(f"   - Y-axis priority heuristic (was X-axis priority)")
                print(f"   - Top alignment preference (was left alignment)")
                print(f"   - Ship constraints integration")
            else:
                print(f"🧠 Algorithm used: Fallback Simple Greedy")
        else:
            print(f"\n❌ No blocks were placed")
        
        input("\n아무 키나 눌러서 종료...")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()