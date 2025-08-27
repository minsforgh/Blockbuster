#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
복셀라이저 방향 선택 로직 디버깅 스크립트
"""
import json
import os
import sys
from pathlib import Path

def analyze_orientation_logic():
    """복셀 캐시 파일들을 분석해서 방향 선택 패턴 찾기"""
    
    voxel_cache_dir = Path("voxel_cache")
    if not voxel_cache_dir.exists():
        print("[ERROR] voxel_cache 폴더를 찾을 수 없습니다")
        return
    
    print("=== 복셀라이저 방향 선택 분석 ===")
    print()
    
    orientation_stats = {
        "original": [],
        "X_rotated": [],
        "Y_rotated": []
    }
    
    aspect_ratio_analysis = []
    
    # 모든 JSON 파일 분석
    for json_file in sorted(voxel_cache_dir.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            block_id = data.get("block_id", "unknown")
            voxel_data = data.get("voxel_data", {})
            
            if not voxel_data:
                continue
                
            orientation = voxel_data.get("selected_orientation", "unknown")
            dimensions = voxel_data.get("dimensions", {})
            
            width = dimensions.get("width", 0)
            height = dimensions.get("height", 0)
            
            if width > 0 and height > 0:
                aspect_ratio = height / width
                
                # 통계에 추가
                if orientation in orientation_stats:
                    orientation_stats[orientation].append(block_id)
                
                aspect_ratio_analysis.append({
                    "block_id": block_id,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "orientation": orientation,
                    "is_tall": height > width
                })
                
        except Exception as e:
            print(f"[WARNING] {json_file.name} 파일 읽기 실패: {e}")
            continue
    
    # 결과 출력
    print("1. 방향별 블록 수:")
    for orientation, blocks in orientation_stats.items():
        print(f"   {orientation}: {len(blocks)}개")
    print()
    
    print("2. 키 큰 블록들의 방향 선택 패턴:")
    tall_blocks = [item for item in aspect_ratio_analysis if item["is_tall"]]
    
    if tall_blocks:
        print(f"   키 큰 블록 총 {len(tall_blocks)}개 중:")
        
        for orientation in ["original", "X_rotated", "Y_rotated"]:
            tall_with_orientation = [b for b in tall_blocks if b["orientation"] == orientation]
            print(f"   - {orientation}: {len(tall_with_orientation)}개")
            
            if tall_with_orientation:
                print("     대표 예시:")
                for block in tall_with_orientation[:3]:  # 상위 3개만
                    print(f"       {block['block_id']}: {block['width']}×{block['height']} (비율 {block['aspect_ratio']:.2f})")
        print()
    
    print("3. 가장 키 큰 블록들 (상위 10개):")
    sorted_by_ratio = sorted(aspect_ratio_analysis, key=lambda x: x["aspect_ratio"], reverse=True)
    for i, block in enumerate(sorted_by_ratio[:10], 1):
        print(f"   {i:2d}. {block['block_id']}: {block['width']}×{block['height']} "
              f"(비율 {block['aspect_ratio']:.2f}) → {block['orientation']}")
    print()
    
    print("4. 방향별 평균 종횡비:")
    for orientation in ["original", "X_rotated", "Y_rotated"]:
        blocks_with_orientation = [b for b in aspect_ratio_analysis if b["orientation"] == orientation]
        if blocks_with_orientation:
            avg_ratio = sum(b["aspect_ratio"] for b in blocks_with_orientation) / len(blocks_with_orientation)
            print(f"   {orientation}: 평균 종횡비 {avg_ratio:.3f}")
    print()
    
    print("5. 결론:")
    tall_original = len([b for b in tall_blocks if b["orientation"] == "original"])
    tall_total = len(tall_blocks)
    
    if tall_total > 0:
        original_percentage = (tall_original / tall_total) * 100
        print(f"   - 키 큰 블록 중 {original_percentage:.1f}%가 'original' 방향으로 선택됨")
        
        if original_percentage > 70:
            print("   - [분석] 대부분의 키 큰 블록이 회전되지 않음")
            print("   - [추정 원인] 3D 복셀에서 XY평면 투영 면적이 다른 방향보다 더 큼")
            print("   - [해결책] 2D 배치를 고려한 방향 선택 로직 필요")
        else:
            print("   - [분석] 키 큰 블록들이 적절히 회전됨")
    
    return aspect_ratio_analysis

if __name__ == "__main__":
    analyze_orientation_logic()