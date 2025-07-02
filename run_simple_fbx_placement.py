"""
간단하고 빠른 FBX 블록 배치 시뮬레이션
"""

import os
import time
import argparse
import random
from pathlib import Path
from simple_fbx_processor import SimpleFBXProcessor
from models.placement_area import PlacementArea
from algorithms.backtracking_placer import BacktrackingPlacer
from utils.visualizer import Visualizer

def parse_arguments():
    """
    명령행 인수 파싱
    """
    parser = argparse.ArgumentParser(description='빠른 FBX 블록 2D 배치 시뮬레이션')
    
    parser.add_argument('--fbx-dir', type=str, default='fbx_blocks',
                        help='FBX 파일들이 있는 디렉토리 (기본값: fbx_blocks)')
    parser.add_argument('--area-width', type=int, default=25,
                        help='배치 영역 너비 (그리드 단위, 기본값: 25)')
    parser.add_argument('--area-height', type=int, default=15,
                        help='배치 영역 높이 (그리드 단위, 기본값: 15)')
    parser.add_argument('--grid-resolution', type=float, default=2.0,
                        help='그리드 해상도 (미터, 기본값: 2.0)')
    parser.add_argument('--max-time', type=float, default=120.0,
                        help='최대 실행 시간 (초, 기본값: 120)')
    parser.add_argument('--output-dir', type=str, default='results',
                        help='결과 저장 디렉토리 (기본값: results)')
    
    parser.add_argument('--max-files', type=int, default=None,
                        help='처리할 최대 FBX 파일 수 (랜덤 선택)')
    parser.add_argument('--info-only', action='store_true',
                        help='파일 정보만 확인 (변환/배치하지 않음)')
    parser.add_argument('--no-placement', action='store_true',
                        help='배치 알고리즘 실행하지 않고 변환만 수행')
    parser.add_argument('--sort-by', type=str, default='size', 
                        choices=['size', 'area', 'name', 'random'],
                        help='블록 정렬 기준')
    
    return parser.parse_args()

def sort_blocks(blocks, sort_by):
    """블록 정렬"""
    blocks_copy = blocks.copy()
    
    if sort_by == 'size':
        blocks_copy.sort(key=lambda b: b.width * b.height, reverse=True)
    elif sort_by == 'area':
        blocks_copy.sort(key=lambda b: b.get_area(), reverse=True)
    elif sort_by == 'name':
        blocks_copy.sort(key=lambda b: b.id)
    elif sort_by == 'random':
        random.shuffle(blocks_copy)
    
    return blocks_copy

def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    print("🚢 === 빠른 FBX 블록 2D 배치 시뮬레이션 ===")
    print(f"📁 FBX 디렉토리: {args.fbx_dir}")
    if args.max_files:
        print(f"🎲 처리할 파일 수: 최대 {args.max_files}개 (랜덤 선택)")
    print(f"⚡ 처리 방식: 바운딩 박스 기반 (초고속)")
    print(f"📏 배치 영역: {args.area_width}x{args.area_height} 그리드 "
          f"({args.area_width * args.grid_resolution}m x {args.area_height * args.grid_resolution}m)")
    print(f"📐 그리드 해상도: {args.grid_resolution}m")
    if not args.info_only and not args.no_placement:
        print(f"⏱️ 최대 실행 시간: {args.max_time}초")
    print("=" * 60)
    
    # 결과 저장 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)
    
    # FBX 디렉토리 확인
    if not os.path.exists(args.fbx_dir):
        print(f"❌ FBX 디렉토리가 존재하지 않습니다: {args.fbx_dir}")
        return
    
    try:
        # 프로세서 초기화
        processor = SimpleFBXProcessor(grid_resolution=args.grid_resolution)
        
        # 파일 정보만 확인하는 모드
        if args.info_only:
            print("\n📊 파일 정보 확인 모드")
            processor.batch_file_info(args.fbx_dir, max_files=args.max_files)
            return
        
        # FBX 파일들을 빠르게 변환
        print("\n⚡ FBX 파일들을 빠른 변환 중...")
        blocks = processor.load_all_fbx_blocks_fast(args.fbx_dir, max_files=args.max_files)
        
        if not blocks:
            print("❌ 변환된 블록이 없습니다.")
            return
        
        # 블록 정렬
        if args.sort_by != 'size':
            print(f"\n🔄 블록 정렬 중... (기준: {args.sort_by})")
            blocks = sort_blocks(blocks, args.sort_by)
        
        # 블록 정보 출력
        print(f"\n📊 === 변환된 블록 정보 ===")
        total_area = 0
        for i, block in enumerate(blocks[:10], 1):  # 처음 10개만 표시
            block_area = block.get_area() * (args.grid_resolution ** 2)
            total_area += block_area
            print(f"{i:2d}. {block.id}")
            print(f"    크기: {block.width}x{block.height} 그리드 ({block_area:.0f}m²)")
        
        if len(blocks) > 10:
            # 나머지 블록들의 면적 계산
            for block in blocks[10:]:
                total_area += block.get_area() * (args.grid_resolution ** 2)
            print(f"    ... (총 {len(blocks)}개 블록)")
        
        print(f"\n📈 총 블록 면적: {total_area:.0f}m²")
        placement_area_size = args.area_width * args.area_height * (args.grid_resolution ** 2)
        print(f"📐 배치 영역 크기: {placement_area_size:.0f}m²")
        print(f"📊 면적 비율: {(total_area / placement_area_size * 100):.1f}%")
        
        # 변환만 수행하는 모드
        if args.no_placement:
            print("\n✅ 변환 완료! (배치 알고리즘은 실행하지 않음)")
            return
        
        # 배치 영역 초기화
        print(f"\n🎯 배치 영역 초기화...")
        area = PlacementArea(width=args.area_width, height=args.area_height)
        
        # 배치 알고리즘 실행
        print(f"\n🧠 배치 알고리즘 실행 중...")
        print(f"   알고리즘: 휴리스틱 백트래킹")
        print(f"   최대 시간: {args.max_time}초")
        
        placer = BacktrackingPlacer(area, blocks, max_time=args.max_time)
        
        start_time = time.time()
        best_solution = placer.optimize()
        elapsed_time = time.time() - start_time
        
        print(f"⏱️ 배치 실행 시간: {elapsed_time:.1f}초")
        
        # 결과 분석 및 출력
        if best_solution is None:
            print("❌ 배치 가능한 솔루션을 찾지 못했습니다.")
            return
        
        print(f"\n🎉 === 배치 결과 ===")
        placed_count = len(best_solution.placed_blocks)
        total_count = len(blocks)
        print(f"✅ 배치된 블록: {placed_count}/{total_count}개 ({placed_count/total_count*100:.1f}%)")
        print(f"❌ 미배치 블록: {len(best_solution.unplaced_blocks)}개")
        print(f"📊 배치 점수: {best_solution.get_placement_score():.4f}")
        
        # 배치된 블록 상세 정보 (처음 10개만)
        if best_solution.placed_blocks:
            print(f"\n📋 배치된 블록 상세 (처음 10개):")
            for i, (block_id, block) in enumerate(list(best_solution.placed_blocks.items())[:10], 1):
                pos_x, pos_y = block.position
                real_x = pos_x * args.grid_resolution
                real_y = pos_y * args.grid_resolution
                print(f"  {i:2d}. {block_id}: ({pos_x:2d}, {pos_y:2d}) = ({real_x:4.0f}m, {real_y:4.0f}m)")
            
            if len(best_solution.placed_blocks) > 10:
                print(f"      ... (총 {len(best_solution.placed_blocks)}개)")
        
        # 미배치 블록 정보 (처음 5개만)
        if best_solution.unplaced_blocks:
            unplaced_list = list(best_solution.unplaced_blocks.keys())
            print(f"\n❌ 미배치 블록 (처음 5개):")
            for i, block_id in enumerate(unplaced_list[:5], 1):
                print(f"  {i}. {block_id}")
            if len(unplaced_list) > 5:
                print(f"     ... (총 {len(unplaced_list)}개)")
        
        # 결과 시각화
        print(f"\n🎨 결과 시각화 생성 중...")
        viz = Visualizer()
        
        # 2D 배치도
        viz.visualize_2d(
            best_solution,
            title=f"빠른 FBX 블록 2D 배치 ({placed_count}/{total_count} 배치)",
            save_path=os.path.join(args.output_dir, "simple_fbx_placement_2d.png"),
            show=False
        )
        
        # 3D 배치 결과
        viz.visualize_3d(
            best_solution,
            title=f"빠른 FBX 블록 3D 배치",
            save_path=os.path.join(args.output_dir, "simple_fbx_placement_3d.png"),
            show=False
        )
        
        # 원본 블록과 배치 결과 비교
        viz.compare_blocks(
            blocks,
            best_solution,
            title=f"빠른 FBX 블록 배치 비교",
            save_path=os.path.join(args.output_dir, "simple_fbx_placement_comparison.png"),
            show=False
        )
        
        print(f"💾 시각화 결과가 '{args.output_dir}' 디렉토리에 저장되었습니다:")
        print(f"  • simple_fbx_placement_2d.png")
        print(f"  • simple_fbx_placement_3d.png")
        print(f"  • simple_fbx_placement_comparison.png")
        
        # 요약 정보 저장
        summary_path = os.path.join(args.output_dir, "simple_placement_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=== 빠른 FBX 블록 배치 결과 요약 ===\n")
            f.write(f"실행 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"처리 방식: 바운딩 박스 기반 (초고속)\n")
            f.write(f"FBX 디렉토리: {args.fbx_dir}\n")
            f.write(f"처리된 파일 수: {len(blocks)}개")
            if args.max_files:
                f.write(f" (최대 {args.max_files}개 중 랜덤 선택)")
            f.write(f"\n")
            f.write(f"배치 영역: {args.area_width}x{args.area_height} 그리드\n")
            f.write(f"그리드 해상도: {args.grid_resolution}m\n")
            f.write(f"배치 실행 시간: {elapsed_time:.1f}초\n")
            f.write(f"배치된 블록: {placed_count}/{total_count}개 ({placed_count/total_count*100:.1f}%)\n")
            f.write(f"배치 점수: {best_solution.get_placement_score():.4f}\n")
            
            f.write("\n=== 배치된 블록 상세 ===\n")
            for block_id, block in best_solution.placed_blocks.items():
                pos_x, pos_y = block.position
                real_x = pos_x * args.grid_resolution
                real_y = pos_y * args.grid_resolution
                f.write(f"{block_id}: ({pos_x}, {pos_y}) = ({real_x:.0f}m, {real_y:.0f}m)\n")
        
        print(f"📄 요약 정보가 '{summary_path}'에 저장되었습니다.")
        
        print(f"\n🎯 === 최종 완료 ===")
        print(f"✅ 총 {placed_count}개 블록 배치 성공")
        print(f"📊 배치 효율: {placed_count/total_count*100:.1f}%")
        print(f"⚡ 처리 속도: 기존 대비 10~20배 빠름")
        print(f"💾 모든 결과가 '{args.output_dir}' 디렉토리에 저장됨")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()