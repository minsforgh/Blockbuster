"""
선박 블록 최적 배치 알고리즘 메인 실행 파일
"""
import time
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt

from models.voxel_block import VoxelBlock
from models.placement_area import PlacementArea
from algorithms.backtracking_placer import BacktrackingPlacer
from utils.visualizer import Visualizer
from utils.random_block_generator import RandomBlockGenerator


def parse_arguments():
    """
    명령행 인수 파싱

    Returns:
        argparse.Namespace: 파싱된 인수
    """
    parser = argparse.ArgumentParser(description='선박 블록 최적 배치 알고리즘')

    parser.add_argument('--width', type=int, default=15,
                        help='배치 영역 너비 (기본값: 15)')
    parser.add_argument('--height', type=int, default=10,
                        help='배치 영역 높이 (기본값: 10)')
    parser.add_argument('--block-count', type=int, default=10,
                        help='블록 수 (기본값: 10)')
    parser.add_argument('--max-block-size', type=int, default=8,
                        help='최대 블록 크기 (기본값: 8)')
    parser.add_argument('--complexity', type=float, default=1.0,
                        help='블록 복잡도 (0.0~2.0, 기본값: 1.0)')
    parser.add_argument('--large-block-bias', type=float, default=0.7,
                        help='대형 블록 생성 비율 (0.0~1.0, 기본값: 0.7)')
    parser.add_argument('--max-time', type=float, default=60.0,
                        help='최대 실행 시간 (초, 기본값: 60.0)')

    parser.add_argument('--use-predefined', action='store_true',
                        help='미리 정의된 블록 세트 사용 여부')
    parser.add_argument('--output-dir', type=str, default='results',
                        help='결과 저장 디렉토리 (기본값: results)')
    parser.add_argument('--no-visualization', action='store_true',
                        help='시각화 비활성화')

    return parser.parse_args()


def main():
    """메인 실행 함수"""
    # 명령행 인수 파싱
    args = parse_arguments()

    # 결과 저장 디렉토리 생성
    os.makedirs(args.output_dir, exist_ok=True)

    print("=== 선박 블록 최적 배치 알고리즘 ===")
    print(f"배치 영역 크기: {args.width}x{args.height}")
    print(f"블록 수: {args.block_count}")
    print(f"최대 블록 크기: {args.max_block_size}")
    print(f"블록 복잡도: {args.complexity}")
    print(f"대형 블록 생성 비율: {args.large_block_bias}")
    print(f"최대 실행 시간: {args.max_time}초")
    print(f"알고리즘: 백트래킹")
    print(f"블록 세트: {'미리 정의된 세트' if args.use_predefined else '임의 생성'}")
    print("=" * 40)

    # 블록 생성
    generator = RandomBlockGenerator(
        complexity=args.complexity,
        large_block_bias=args.large_block_bias
    )

    if args.use_predefined:
        blocks = generator.generate_predefined_blocks()
    else:
        blocks = generator.generate_blocks(
            count=args.block_count,
            max_size=args.max_block_size
        )

    # 블록 정보 출력
    print("\n=== 블록 정보 ===")
    for block in blocks:
        print(f"{block}")
    print("=" * 40)

    # 배치 영역 초기화
    area = PlacementArea(width=args.width, height=args.height)

    # 배치 알고리즘 실행
    placer = BacktrackingPlacer(area, blocks, max_time=args.max_time)

    print("\n배치 알고리즘 실행 중...")
    start_time = time.time()

    best_solution = placer.optimize()

    elapsed_time = time.time() - start_time

    print(f"실행 시간: {elapsed_time:.2f}초")

    if best_solution is None:
        print("배치 가능한 솔루션을 찾지 못했습니다.")
        print("=" * 40)
        print("\n프로그램 종료")
        return

    print(f"배치된 블록 수: {len(best_solution.placed_blocks)}/{len(blocks)}")
    print(f"미배치 블록 수: {len(best_solution.unplaced_blocks)}")
    print(f"배치 점수: {best_solution.get_placement_score():.4f}")
    print("=" * 40)

    # 결과 시각화
    if not args.no_visualization:
        print("\n결과 시각화 중...")
        viz = Visualizer()

        # 2D 배치도 시각화
        viz.visualize_2d(
            best_solution,
            title="2D Block Placement",
            save_path=os.path.join(args.output_dir, "placement_2d.png")
        )

        # 3D 배치 결과 시각화
        viz.visualize_3d(
            best_solution,
            title="3D Block Placement",
            save_path=os.path.join(args.output_dir, "placement_3d.png")
        )

        # 원본 블록과 배치 결과 비교 시각화
        viz.compare_blocks(
            blocks,
            best_solution,
            title="Block Placement Comparison",
            save_path=os.path.join(args.output_dir, "placement_comparison.png")
        )

        print(f"시각화 결과가 '{args.output_dir}' 디렉토리에 저장되었습니다.")

    print("\n=== 배치 결과 요약 ===")
    print(f"총 블록 수: {len(blocks)}")
    print(f"배치된 블록 수: {len(best_solution.placed_blocks)}")
    print(f"배치율: {len(best_solution.placed_blocks) / len(blocks) * 100:.2f}%")

    # 배치된 블록 목록
    print("\n배치된 블록:")
    for block_id, block in best_solution.placed_blocks.items():
        print(f"  - {block_id}: 위치 {block.position}, 회전 {block.rotation}°")

    # 미배치 블록 목록
    if best_solution.unplaced_blocks:
        print("\n미배치 블록:")
        for block_id in best_solution.unplaced_blocks:
            print(f"  - {block_id}")

    print("\n프로그램 종료")


if __name__ == "__main__":
    main()
