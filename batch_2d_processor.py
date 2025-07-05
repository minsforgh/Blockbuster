"""
디렉토리 일괄 2D 블록 처리기 + 결과 정리 시스템
모든 FBX/OBJ 파일을 2D 직사각형으로 변환하고 보기 좋게 정리
"""
import trimesh
import numpy as np
import sys
import os
import time
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from collections import defaultdict, Counter
import warnings

warnings.filterwarnings('ignore')

# 프로젝트 모듈 import
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from models.voxel_block import VoxelBlock
    from models.placement_area import PlacementArea
    from algorithms.backtracking_placer import BacktrackingPlacer
    from utils.visualizer import Visualizer
    print(f"[INFO] Project modules loaded successfully")
except ImportError as e:
    print(f"[ERROR] Cannot find project modules: {e}")
    print(f"[INFO] Continuing without placement testing...")

class BatchBlock2DProcessor:
    """디렉토리 내 모든 블록을 2D로 일괄 처리하는 클래스"""
    
    def __init__(self, grid_resolution=2.0, output_dir="2d_blocks_output"):
        """
        Args:
            grid_resolution (float): 그리드 해상도 (m)
            output_dir (str): 결과 저장 디렉토리
        """
        self.grid_resolution = grid_resolution
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 결과 저장용
        self.processed_blocks = []
        self.processing_stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }
        self.error_log = []
    
    def find_mesh_files(self, directory):
        """디렉토리에서 메시 파일들 찾기"""
        directory = Path(directory)
        
        if not directory.exists():
            print(f"❌ Directory not found: {directory}")
            return []
        
        # 지원하는 파일 확장자 (FBX 포함)
        supported_extensions = ['.fbx', '.obj', '.ply', '.stl', '.dae', '.3ds']
        
        mesh_files = []
        for ext in supported_extensions:
            mesh_files.extend(list(directory.glob(f"*{ext}")))
            mesh_files.extend(list(directory.glob(f"*{ext.upper()}")))
        
        # 중복 제거 및 정렬
        mesh_files = sorted(list(set(mesh_files)))
        
        print(f"📁 Found {len(mesh_files)} mesh files in {directory}")
        if len(mesh_files) > 0:
            print(f"   Extensions: {set(f.suffix.lower() for f in mesh_files)}")
            
            # FBX 파일이 있으면 Blender 필요 알림
            fbx_files = [f for f in mesh_files if f.suffix.lower() == '.fbx']
            if fbx_files:
                print(f"   🔄 Found {len(fbx_files)} FBX files - will auto-convert with Blender")
        
        return mesh_files
    
    def process_single_mesh_to_2d(self, file_path):
        """단일 메시 파일을 2D 블록으로 변환"""
        try:
            # 1. FBX 파일인 경우 먼저 OBJ로 변환
            actual_file_path = file_path
            if file_path.suffix.lower() == '.fbx':
                print(f"    🔄 Converting FBX to OBJ...")
                obj_path = self._convert_fbx_to_obj(file_path)
                if obj_path and obj_path.exists():
                    actual_file_path = obj_path
                    print(f"    ✅ FBX conversion successful")
                else:
                    raise Exception("FBX to OBJ conversion failed")
            
            # 2. 메시 로드
            mesh = trimesh.load(actual_file_path)
            
            # 메시 품질 개선
            if hasattr(mesh, 'vertices') and hasattr(mesh, 'faces'):
                mesh.merge_vertices()
                mesh.remove_degenerate_faces()
                mesh.remove_duplicate_faces()
            
            # 2. 바운딩 박스 계산
            bbox_3d = mesh.bounds
            
            # 3. X, Y 크기 추출
            x_size = bbox_3d[1][0] - bbox_3d[0][0]
            y_size = bbox_3d[1][1] - bbox_3d[0][1]
            z_size = bbox_3d[1][2] - bbox_3d[0][2]
            
            # 4. 그리드 단위로 변환
            grid_x = max(1, round(x_size / self.grid_resolution))
            grid_y = max(1, round(y_size / self.grid_resolution))
            
            # 5. 2D 복셀 데이터 생성
            voxel_data_2d = []
            for x in range(grid_x):
                for y in range(grid_y):
                    voxel_data_2d.append((x, y, [0, 1, 0]))
            
            # 6. VoxelBlock 생성
            block_id = file_path.stem
            voxel_block = VoxelBlock(block_id, voxel_data_2d)
            
            # 7. 추가 정보 저장
            block_info = {
                'file_path': str(file_path),
                'block_id': block_id,
                'file_size_mb': file_path.stat().st_size / 1024 / 1024,
                'vertices_count': len(mesh.vertices) if hasattr(mesh, 'vertices') else 0,
                'faces_count': len(mesh.faces) if hasattr(mesh, 'faces') else 0,
                'original_size_3d': {
                    'x': float(x_size),
                    'y': float(y_size),
                    'z': float(z_size)
                },
                'grid_size_2d': {
                    'width': grid_x,
                    'height': grid_y
                },
                'actual_size_2d': {
                    'width': grid_x * self.grid_resolution,
                    'height': grid_y * self.grid_resolution
                },
                'area_cells': grid_x * grid_y,
                'area_m2': (grid_x * self.grid_resolution) * (grid_y * self.grid_resolution)
            }
            
            return voxel_block, block_info, None
            
        except Exception as e:
            error_msg = f"Failed to process {file_path.name}: {str(e)}"
            return None, None, error_msg
    
    def _convert_fbx_to_obj(self, fbx_path):
        """FBX를 OBJ로 변환 (Blender 사용)"""
        try:
            # OBJ 파일 저장 경로 (converted_obj 폴더에 저장)
            converted_dir = fbx_path.parent / "converted_obj"
            converted_dir.mkdir(exist_ok=True)
            obj_path = converted_dir / fbx_path.with_suffix('.obj').name
            
            # 이미 변환된 OBJ 파일이 있으면 사용
            if obj_path.exists():
                obj_time = obj_path.stat().st_mtime
                fbx_time = fbx_path.stat().st_mtime
                if obj_time > fbx_time:  # OBJ가 더 최신이면
                    print(f"        📁 Using cached OBJ: {obj_path.name}")
                    return obj_path
            
            # Blender로 변환
            print(f"        🔄 Converting to: {obj_path.relative_to(fbx_path.parent)}")
            success = self._run_blender_conversion(fbx_path, obj_path)
            
            if success and obj_path.exists():
                return obj_path
            else:
                return None
                
        except Exception as e:
            print(f"        ❌ FBX conversion error: {e}")
            return None
    
    def _run_blender_conversion(self, fbx_path, obj_path):
        """Blender를 실행해서 FBX → OBJ 변환"""
        try:
            import subprocess
            import tempfile
            
            # Blender 스크립트 생성
            blender_script = f'''
import bpy
import sys

# FBX 임포트
bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.fbx(filepath="{str(fbx_path).replace(chr(92), "/")}")
    # OBJ 익스포트
    bpy.ops.wm.obj_export(
        filepath="{str(obj_path).replace(chr(92), "/")}",
        export_selected_objects=True,
        export_uv=False,
        export_normals=True,
        export_materials=False,
        export_triangulated_mesh=True
    )
    print("SUCCESS: FBX to OBJ conversion completed")
except Exception as e:
    print(f"ERROR: {{e}}")
    sys.exit(1)
'''
            
            # 임시 스크립트 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(blender_script)
                script_path = f.name
            
            # Blender 실행
            blender_paths = [
                "blender",  # PATH에 있는 경우
                r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
                "/Applications/Blender.app/Contents/MacOS/Blender",
                "/usr/bin/blender"
            ]
            
            for blender_path in blender_paths:
                try:
                    cmd = [
                        blender_path,
                        "--background",
                        "--python", script_path
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    # 임시 파일 정리
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                    
                    if result.returncode == 0 and "SUCCESS" in result.stdout:
                        return True
                    
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            # 모든 Blender 경로가 실패한 경우
            print(f"        ⚠️ Blender not found. Please install Blender or add to PATH")
            return False
            
        except Exception as e:
            print(f"        ❌ Blender execution error: {e}")
            return False
    
    def classify_block_by_name(self, block_id):
        """블록 이름으로 유형 분류"""
        # 파일명에서 블록 번호 추출 시도
        block_id_lower = block_id.lower()
        
        # 패턴 매칭
        if any(char.isalpha() for char in block_id):
            # 영문 포함 (예: 20F, 20G, 20Y, 40A)
            return "crane"
        elif block_id.isdigit():
            # 순수 숫자
            if len(block_id) <= 2:
                return "crane"  # 10단위
            else:
                return "trestle"  # 100단위
        else:
            # 복합 패턴 (예: 4386_183_000)
            parts = block_id.replace('_', '').replace('-', '')
            if any(part.isdigit() and len(part) >= 3 for part in parts.split()):
                return "trestle"
            else:
                return "crane"
    
    def process_directory(self, directory):
        """디렉토리 내 모든 메시 파일을 2D로 변환"""
        print(f"\n🚀 Starting batch 2D block processing...")
        print(f"📁 Directory: {directory}")
        print(f"📐 Grid resolution: {self.grid_resolution}m")
        print(f"💾 Output: {self.output_dir}")
        print("="*80)
        
        # 시작 시간 기록
        self.processing_stats['start_time'] = time.time()
        
        # 메시 파일들 찾기
        mesh_files = self.find_mesh_files(directory)
        self.processing_stats['total_files'] = len(mesh_files)
        
        if not mesh_files:
            print("❌ No mesh files found!")
            return
        
        # 각 파일 처리
        print(f"\n🔄 Processing {len(mesh_files)} files...")
        for i, file_path in enumerate(mesh_files, 1):
            print(f"\n📦 [{i:3d}/{len(mesh_files)}] {file_path.name}")
            
            # 파일 크기 체크
            file_size_mb = file_path.stat().st_size / 1024 / 1024
            print(f"    💾 Size: {file_size_mb:.1f}MB")
            
            # 너무 큰 파일은 건너뛰기 (500MB 이상)
            if file_size_mb > 500:
                print(f"    ⚠️ Skipped: File too large (>{500}MB)")
                self.processing_stats['skipped'] += 1
                continue
            
            # 처리 시작
            start_time = time.time()
            voxel_block, block_info, error = self.process_single_mesh_to_2d(file_path)
            elapsed_time = time.time() - start_time
            
            if voxel_block and block_info:
                # 성공
                block_info['processing_time'] = elapsed_time
                block_info['block_type'] = self.classify_block_by_name(block_info['block_id'])
                
                self.processed_blocks.append({
                    'voxel_block': voxel_block,
                    'info': block_info
                })
                
                self.processing_stats['successful'] += 1
                
                print(f"    ✅ Success: {block_info['grid_size_2d']['width']}×{block_info['grid_size_2d']['height']} "
                      f"({block_info['area_cells']} cells, {elapsed_time:.1f}s, {block_info['block_type']})")
            else:
                # 실패
                self.error_log.append({
                    'file': str(file_path),
                    'error': error,
                    'timestamp': time.time()
                })
                self.processing_stats['failed'] += 1
                print(f"    ❌ Failed: {error}")
        
        # 종료 시간 기록
        self.processing_stats['end_time'] = time.time()
        
        print(f"\n🎉 Batch processing complete!")
        self._print_processing_summary()
        
        # 결과 저장
        self._save_results()
        
        # 시각화 생성
        self._create_visualizations()
        
        return self.processed_blocks
    
    def _print_processing_summary(self):
        """처리 결과 요약 출력"""
        total_time = self.processing_stats['end_time'] - self.processing_stats['start_time']
        
        print("\n📊 PROCESSING SUMMARY")
        print("="*50)
        print(f"⏱️  Total time: {total_time:.1f}s")
        print(f"📁 Total files: {self.processing_stats['total_files']}")
        print(f"✅ Successful: {self.processing_stats['successful']}")
        print(f"❌ Failed: {self.processing_stats['failed']}")
        print(f"⚠️  Skipped: {self.processing_stats['skipped']}")
        print(f"📈 Success rate: {self.processing_stats['successful']/max(1,self.processing_stats['total_files'])*100:.1f}%")
        
        if self.processed_blocks:
            # 블록 통계
            crane_blocks = [b for b in self.processed_blocks if b['info']['block_type'] == 'crane']
            trestle_blocks = [b for b in self.processed_blocks if b['info']['block_type'] == 'trestle']
            
            total_area = sum(b['info']['area_cells'] for b in self.processed_blocks)
            avg_area = total_area / len(self.processed_blocks)
            
            print(f"\n🏗️  Block Statistics:")
            print(f"    🔧 Crane blocks: {len(crane_blocks)}")
            print(f"    🚚 Trestle blocks: {len(trestle_blocks)}")
            print(f"    📐 Average area: {avg_area:.1f} cells")
            print(f"    📊 Total area: {total_area:,} cells")
            
            # 크기 분포
            sizes = [f"{b['info']['grid_size_2d']['width']}×{b['info']['grid_size_2d']['height']}" 
                    for b in self.processed_blocks]
            size_counts = Counter(sizes)
            print(f"    📏 Most common sizes:")
            for size, count in size_counts.most_common(5):
                print(f"        {size}: {count} blocks")
    
    def _save_results(self):
        """결과를 다양한 형태로 저장"""
        print(f"\n💾 Saving results to {self.output_dir}...")
        
        # 1. JSON 상세 정보 저장
        json_data = {
            'processing_stats': self.processing_stats,
            'blocks': [b['info'] for b in self.processed_blocks],
            'errors': self.error_log,
            'metadata': {
                'grid_resolution': self.grid_resolution,
                'timestamp': time.time(),
                'total_blocks': len(self.processed_blocks)
            }
        }
        
        json_path = self.output_dir / 'block_processing_results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"    💾 JSON: {json_path}")
        
        # 2. CSV 요약 정보 저장
        if self.processed_blocks:
            csv_data = []
            for block_data in self.processed_blocks:
                info = block_data['info']
                csv_data.append({
                    'block_id': info['block_id'],
                    'block_type': info['block_type'],
                    'grid_width': info['grid_size_2d']['width'],
                    'grid_height': info['grid_size_2d']['height'],
                    'area_cells': info['area_cells'],
                    'area_m2': info['area_m2'],
                    'original_x': info['original_size_3d']['x'],
                    'original_y': info['original_size_3d']['y'],
                    'original_z': info['original_size_3d']['z'],
                    'vertices': info['vertices_count'],
                    'faces': info['faces_count'],
                    'file_size_mb': info['file_size_mb'],
                    'processing_time': info['processing_time']
                })
            
            df = pd.DataFrame(csv_data)
            csv_path = self.output_dir / 'blocks_summary.csv'
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"    📊 CSV: {csv_path}")
        
        # 3. 텍스트 리포트 저장
        report_path = self.output_dir / 'processing_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("🚀 2D BLOCK PROCESSING REPORT\n")
            f.write("="*50 + "\n\n")
            
            # 처리 통계
            f.write("📊 PROCESSING STATISTICS\n")
            f.write("-"*30 + "\n")
            f.write(f"Total files: {self.processing_stats['total_files']}\n")
            f.write(f"Successful: {self.processing_stats['successful']}\n")
            f.write(f"Failed: {self.processing_stats['failed']}\n")
            f.write(f"Skipped: {self.processing_stats['skipped']}\n")
            f.write(f"Success rate: {self.processing_stats['successful']/max(1,self.processing_stats['total_files'])*100:.1f}%\n\n")
            
            # 블록 목록
            if self.processed_blocks:
                f.write("📦 PROCESSED BLOCKS\n")
                f.write("-"*30 + "\n")
                for block_data in self.processed_blocks:
                    info = block_data['info']
                    f.write(f"{info['block_id']:20} | {info['block_type']:8} | "
                           f"{info['grid_size_2d']['width']:2}×{info['grid_size_2d']['height']:2} | "
                           f"{info['area_cells']:3} cells | {info['processing_time']:.1f}s\n")
            
            # 에러 목록
            if self.error_log:
                f.write(f"\n❌ ERRORS ({len(self.error_log)})\n")
                f.write("-"*30 + "\n")
                for error in self.error_log:
                    f.write(f"{Path(error['file']).name}: {error['error']}\n")
        
        print(f"    📄 Report: {report_path}")
    
    def _create_visualizations(self):
        """처리 결과 시각화 생성"""
        if not self.processed_blocks:
            return
        
        print(f"\n🎨 Creating visualizations...")
        
        # 그림 크기 설정
        fig = plt.figure(figsize=(20, 12))
        
        # 1. 블록 크기 분포 (2×2 그리드의 첫 번째)
        ax1 = plt.subplot(2, 3, 1)
        areas = [b['info']['area_cells'] for b in self.processed_blocks]
        ax1.hist(areas, bins=min(20, len(set(areas))), alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_xlabel('Area (cells)')
        ax1.set_ylabel('Count')
        ax1.set_title('📐 Block Size Distribution')
        ax1.grid(True, alpha=0.3)
        
        # 2. 블록 유형 분포 (파이 차트)
        ax2 = plt.subplot(2, 3, 2)
        type_counts = Counter(b['info']['block_type'] for b in self.processed_blocks)
        colors = ['lightcoral', 'lightblue', 'lightgreen']
        wedges, texts, autotexts = ax2.pie(type_counts.values(), labels=type_counts.keys(), 
                                          autopct='%1.1f%%', colors=colors[:len(type_counts)])
        ax2.set_title('🏗️ Block Type Distribution')
        
        # 3. 처리 시간 분포
        ax3 = plt.subplot(2, 3, 3)
        times = [b['info']['processing_time'] for b in self.processed_blocks]
        ax3.scatter(range(len(times)), times, alpha=0.6, c='orange')
        ax3.set_xlabel('Block Index')
        ax3.set_ylabel('Processing Time (s)')
        ax3.set_title('⏱️ Processing Time')
        ax3.grid(True, alpha=0.3)
        
        # 4. 블록 크기 vs 처리 시간
        ax4 = plt.subplot(2, 3, 4)
        vertices = [b['info']['vertices_count'] for b in self.processed_blocks]
        ax4.scatter(vertices, times, alpha=0.6, c='green')
        ax4.set_xlabel('Vertices Count')
        ax4.set_ylabel('Processing Time (s)')
        ax4.set_title('🔺 Vertices vs Processing Time')
        ax4.grid(True, alpha=0.3)
        
        # 5. 2D 블록 배치 미리보기 (일부만)
        ax5 = plt.subplot(2, 3, 5)
        preview_blocks = self.processed_blocks[:12]  # 처음 12개만
        
        cols = 4
        rows = 3
        colors = plt.cm.Set3(np.linspace(0, 1, len(preview_blocks)))
        
        for i, block_data in enumerate(preview_blocks):
            row = i // cols
            col = i % cols
            
            info = block_data['info']
            width = info['grid_size_2d']['width']
            height = info['grid_size_2d']['height']
            
            # 위치 계산
            x = col * 6
            y = (rows - 1 - row) * 6
            
            # 블록 그리기
            rect = patches.Rectangle((x, y), width, height, 
                                   linewidth=1, edgecolor='black', 
                                   facecolor=colors[i], alpha=0.7)
            ax5.add_patch(rect)
            
            # 블록 ID 표시
            ax5.text(x + width/2, y + height/2, info['block_id'][:8], 
                    ha='center', va='center', fontsize=6, fontweight='bold')
        
        ax5.set_xlim(0, cols * 6)
        ax5.set_ylim(0, rows * 6)
        ax5.set_aspect('equal')
        ax5.set_title('📦 Block Preview (First 12)')
        ax5.grid(True, alpha=0.3)
        
        # 6. 요약 통계 텍스트
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        
        total_area = sum(b['info']['area_cells'] for b in self.processed_blocks)
        avg_area = total_area / len(self.processed_blocks)
        total_time = sum(b['info']['processing_time'] for b in self.processed_blocks)
        
        stats_text = f"""
📊 SUMMARY STATISTICS

🔢 Total Blocks: {len(self.processed_blocks)}
📐 Total Area: {total_area:,} cells
📏 Average Area: {avg_area:.1f} cells
⏱️ Total Processing: {total_time:.1f}s
📈 Success Rate: {self.processing_stats['successful']/max(1,self.processing_stats['total_files'])*100:.1f}%

🏗️ Block Types:
"""
        
        type_counts = Counter(b['info']['block_type'] for b in self.processed_blocks)
        for block_type, count in type_counts.items():
            stats_text += f"   {block_type}: {count}\n"
        
        ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, fontsize=10, 
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray"))
        
        plt.suptitle('🎯 2D Block Processing Results Dashboard', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        # 저장
        viz_path = self.output_dir / 'processing_dashboard.png'
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"    🎨 Dashboard: {viz_path}")
    
    def get_blocks_for_placement(self):
        """배치 알고리즘용 블록 리스트 반환"""
        if not self.processed_blocks:
            return []
        
        # VoxelBlock 객체들만 추출
        blocks = [b['voxel_block'] for b in self.processed_blocks]
        
        # 블록에 추가 정보 첨부
        for i, block_data in enumerate(self.processed_blocks):
            blocks[i].block_type = block_data['info']['block_type']
            blocks[i].original_info = block_data['info']
        
        return blocks

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("🚀" + "="*70)
        print("BATCH 2D BLOCK PROCESSOR")
        print("🚀" + "="*70)
        print("")
        print("사용법:")
        print("  python batch_2d_processor.py <directory>")
        print("  python batch_2d_processor.py <directory> <resolution>")
        print("  python batch_2d_processor.py <directory> <resolution> <output_dir>")
        print("")
        print("예시:")
        print("  python batch_2d_processor.py fbx_blocks/")
        print("  python batch_2d_processor.py models/ 1.5")
        print("  python batch_2d_processor.py blocks/ 2.0 results/")
        print("")
        print("✨ 기능:")
        print("  📁 디렉토리 내 모든 메시 파일 일괄 처리")
        print("  📐 2D 직사각형 블록으로 변환")
        print("  🏗️ 크레인/트레슬 블록 자동 분류")
        print("  📊 상세 통계 및 시각화")
        print("  💾 JSON, CSV, TXT 결과 저장")
        print("  🎨 대시보드 차트 생성")
        return
    
    # 인수 파싱
    directory = sys.argv[1]
    resolution = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "2d_blocks_output"
    
    try:
        print("🚀" + "="*70)
        print("BATCH 2D BLOCK PROCESSOR")
        print("🚀" + "="*70)
        
        # 처리기 생성
        processor = BatchBlock2DProcessor(
            grid_resolution=resolution,
            output_dir=output_dir
        )
        
        # 일괄 처리 실행
        processed_blocks = processor.process_directory(directory)
        
        if processed_blocks:
            print(f"\n🎉 === PROCESSING COMPLETE! ===")
            print(f"✅ Successfully processed {len(processed_blocks)} blocks")
            print(f"📁 Results saved to: {processor.output_dir}")
            print(f"🎨 Dashboard chart created")
            
            # 배치 알고리즘 테스트 제안
            print(f"\n💡 Next Steps:")
            print(f"  🔧 Use processed blocks with placement algorithm")
            print(f"  📊 Check dashboard: {processor.output_dir}/processing_dashboard.png")
            print(f"  📋 Review CSV: {processor.output_dir}/blocks_summary.csv")
            
            # 간단한 배치 테스트 (선택사항)
            try:
                blocks = processor.get_blocks_for_placement()
                if len(blocks) > 0:
                    print(f"\n🧪 Testing placement with first 5 blocks...")
                    
                    # 자항선 크기: 84m×36m = 42×18 그리드
                    test_area = PlacementArea(width=42, height=18)
                    test_blocks = blocks[:5]  # 처음 5개만 테스트
                    
                    placer = BacktrackingPlacer(test_area, test_blocks, max_time=10)
                    result = placer.optimize()
                    
                    if result:
                        print(f"    ✅ Placement test successful!")
                        print(f"    📦 Placed: {len(result.placed_blocks)}/{len(test_blocks)} blocks")
                        print(f"    📊 Score: {result.get_placement_score():.3f}")
                    else:
                        print(f"    ⚠️ Placement test: no solution found")
            except:
                print(f"    ℹ️ Placement test skipped (modules not available)")
        
        else:
            print(f"\n💡 Processing completed but no blocks were successfully converted.")
            print(f"📋 Check error log: {processor.output_dir}/processing_report.txt")
        
        input("\n아무 키나 눌러서 종료...")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()