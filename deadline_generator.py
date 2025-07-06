#!/usr/bin/env python3
"""
CSV 납기기한 추가 생성기
blocks_summary.csv 파일을 읽어서 납기기한(deadline) 컬럼을 추가한 새로운 CSV 파일을 생성합니다.

사용법:
    python deadline_generator.py input.csv [output.csv] [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD]

예시:
    python deadline_generator.py blocks_summary.csv
    python deadline_generator.py blocks_summary.csv blocks_with_deadlines.csv
    python deadline_generator.py blocks_summary.csv --start-date 2025-06-01 --end-date 2025-12-31
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import random
from pathlib import Path

class DeadlineGenerator:
    """
    블록 데이터에 납기기한을 추가하는 클래스
    """
    
    def __init__(self, start_date="2025-06-01", end_date="2025-12-31"):
        """
        초기화
        
        Args:
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
        """
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(end_date, "%Y-%m-%d")
        self.deadline_dates = self._generate_deadline_dates()
        
    def _generate_deadline_dates(self):
        """
        7일 간격으로 납기일 목록 생성
        
        Returns:
            list: 날짜 문자열 목록
        """
        dates = []
        current_date = self.start_date
        
        # 첫 번째 수요일 찾기 (weekday 2 = 수요일)
        while current_date.weekday() != 2:
            current_date += timedelta(days=1)
        
        # 7일 간격으로 날짜 생성
        while current_date <= self.end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=7)
            
        return dates
    
    def _assign_deadlines_smart(self, df):
        """
        스마트 납기일 할당
        - 크레인 블록은 후반부에 집중
        - 트레슬 블록은 전체적으로 분산
        - 2-3개씩 그룹화
        
        Args:
            df (DataFrame): 블록 데이터프레임
            
        Returns:
            list: 각 블록의 납기일 목록
        """
        crane_blocks = df[df['block_type'] == 'crane'].index.tolist()
        trestle_blocks = df[df['block_type'] == 'trestle'].index.tolist()
        
        # 날짜를 전반부(40%), 중반부(30%), 후반부(30%)로 분할
        total_dates = len(self.deadline_dates)
        early_dates = self.deadline_dates[:int(total_dates * 0.4)]
        mid_dates = self.deadline_dates[int(total_dates * 0.4):int(total_dates * 0.7)]
        late_dates = self.deadline_dates[int(total_dates * 0.7):]
        
        deadlines = [None] * len(df)
        
        # 크레인 블록: 중반부(30%) + 후반부(70%)에 집중
        crane_dates = mid_dates + late_dates
        random.shuffle(crane_dates)
        
        # 트레슬 블록: 전체 기간에 고르게 분산
        trestle_dates = self.deadline_dates.copy()
        random.shuffle(trestle_dates)
        
        # 크레인 블록 할당 (2-3개씩 그룹화)
        crane_idx = 0
        date_idx = 0
        while crane_idx < len(crane_blocks):
            if date_idx >= len(crane_dates):
                date_idx = 0  # 날짜 목록을 다시 순환
                
            current_date = crane_dates[date_idx]
            blocks_per_date = random.randint(2, 3)  # 2-3개씩 그룹화
            
            for _ in range(blocks_per_date):
                if crane_idx < len(crane_blocks):
                    deadlines[crane_blocks[crane_idx]] = current_date
                    crane_idx += 1
            
            date_idx += 1
        
        # 트레슬 블록 할당 (2-3개씩 그룹화)
        trestle_idx = 0
        date_idx = 0
        while trestle_idx < len(trestle_blocks):
            if date_idx >= len(trestle_dates):
                date_idx = 0  # 날짜 목록을 다시 순환
                
            current_date = trestle_dates[date_idx]
            blocks_per_date = random.randint(2, 3)  # 2-3개씩 그룹화
            
            for _ in range(blocks_per_date):
                if trestle_idx < len(trestle_blocks):
                    deadlines[trestle_blocks[trestle_idx]] = current_date
                    trestle_idx += 1
            
            date_idx += 1
        
        return deadlines
    
    def process_csv(self, input_file, output_file=None):
        """
        CSV 파일 처리
        
        Args:
            input_file (str): 입력 CSV 파일 경로
            output_file (str): 출력 CSV 파일 경로 (기본값: input_with_deadlines.csv)
            
        Returns:
            tuple: (처리된 DataFrame, 출력 파일 경로)
        """
        try:
            # CSV 파일 읽기
            print(f"📁 입력 파일 읽는 중: {input_file}")
            df = pd.read_csv(input_file)
            
            print(f"✅ {len(df)}개 블록 데이터 로드됨")
            
            # 블록 유형 확인
            if 'block_type' not in df.columns:
                print("⚠️ 경고: 'block_type' 컬럼이 없습니다. 모든 블록을 'trestle'로 처리합니다.")
                df['block_type'] = 'trestle'
            
            type_counts = df['block_type'].value_counts()
            print(f"📊 블록 유형 분포:")
            for block_type, count in type_counts.items():
                print(f"   - {block_type}: {count}개")
            
            # 납기일 할당
            print(f"📅 납기기한 할당 중... ({self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')})")
            print(f"   📋 총 {len(self.deadline_dates)}개 납기일 생성됨")
            
            # 시드 설정 (재현 가능한 결과)
            random.seed(42)
            np.random.seed(42)
            
            deadlines = self._assign_deadlines_smart(df)
            df['deadline'] = deadlines
            
            # 납기일별 통계
            deadline_counts = df['deadline'].value_counts().sort_index()
            print(f"\n📈 납기일별 블록 분포:")
            for date, count in deadline_counts.items():
                month = date[:7]
                print(f"   - {date}: {count}개 블록")
            
            # 월별 통계
            df['month'] = df['deadline'].str[:7]
            monthly_counts = df['month'].value_counts().sort_index()
            print(f"\n📊 월별 블록 분포:")
            for month, count in monthly_counts.items():
                print(f"   - {month}: {count}개 블록")
            
            # 출력 파일명 결정
            if output_file is None:
                input_path = Path(input_file)
                output_file = input_path.parent / f"{input_path.stem}_with_deadlines{input_path.suffix}"
            
            # CSV 파일 저장
            print(f"\n💾 결과 저장 중: {output_file}")
            df_output = df.drop('month', axis=1)  # 임시 컬럼 제거
            df_output.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"✅ 완료! 납기기한이 추가된 {len(df_output)}개 블록 데이터가 저장되었습니다.")
            
            return df_output, str(output_file)
            
        except FileNotFoundError:
            print(f"❌ 오류: 파일 '{input_file}'을 찾을 수 없습니다.")
            return None, None
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            return None, None
    
    def generate_summary_report(self, df, output_file):
        """
        요약 보고서 생성
        
        Args:
            df (DataFrame): 처리된 데이터프레임
            output_file (str): 출력 파일 경로
        """
        try:
            report_file = Path(output_file).parent / f"{Path(output_file).stem}_report.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("선박 블록 납기기한 할당 보고서\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"📊 전체 통계:\n")
                f.write(f"   - 총 블록 수: {len(df)}개\n")
                f.write(f"   - 납기 기간: {df['deadline'].min()} ~ {df['deadline'].max()}\n")
                f.write(f"   - 총 납기일 수: {df['deadline'].nunique()}개\n\n")
                
                f.write(f"🏗️ 블록 유형별 분포:\n")
                type_counts = df['block_type'].value_counts()
                for block_type, count in type_counts.items():
                    percentage = (count / len(df)) * 100
                    f.write(f"   - {block_type}: {count}개 ({percentage:.1f}%)\n")
                f.write("\n")
                
                f.write(f"📅 월별 분포:\n")
                df_temp = df.copy()
                df_temp['month'] = df_temp['deadline'].str[:7]
                monthly_counts = df_temp['month'].value_counts().sort_index()
                for month, count in monthly_counts.items():
                    percentage = (count / len(df)) * 100
                    f.write(f"   - {month}: {count}개 ({percentage:.1f}%)\n")
                f.write("\n")
                
                f.write(f"📋 납기일별 상세 분포:\n")
                deadline_counts = df['deadline'].value_counts().sort_index()
                for date, count in deadline_counts.items():
                    crane_count = len(df[(df['deadline'] == date) & (df['block_type'] == 'crane')])
                    trestle_count = len(df[(df['deadline'] == date) & (df['block_type'] == 'trestle')])
                    f.write(f"   - {date}: {count}개 (크레인: {crane_count}, 트레슬: {trestle_count})\n")
                
                f.write(f"\n" + "=" * 60 + "\n")
                f.write(f"보고서 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"📋 요약 보고서 생성됨: {report_file}")
            
        except Exception as e:
            print(f"⚠️ 보고서 생성 오류: {str(e)}")

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="블록 데이터 CSV에 납기기한을 추가합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python deadline_generator.py blocks_summary.csv
  python deadline_generator.py blocks_summary.csv output.csv
  python deadline_generator.py input.csv --start-date 2025-06-01 --end-date 2025-12-31
  python deadline_generator.py input.csv --start-date 2025-07-01 --end-date 2026-03-31
        """
    )
    
    parser.add_argument('input_file', 
                       help='입력 CSV 파일 경로')
    parser.add_argument('output_file', 
                       nargs='?', 
                       default=None,
                       help='출력 CSV 파일 경로 (기본값: input_with_deadlines.csv)')
    parser.add_argument('--start-date', 
                       default='2025-06-01',
                       help='시작 날짜 (YYYY-MM-DD, 기본값: 2025-06-01)')
    parser.add_argument('--end-date', 
                       default='2025-12-31',
                       help='종료 날짜 (YYYY-MM-DD, 기본값: 2025-12-31)')
    parser.add_argument('--seed',
                       type=int,
                       default=42,
                       help='랜덤 시드 (재현 가능한 결과용, 기본값: 42)')
    
    # 도움말 출력
    if len(sys.argv) == 1:
        print("🚢 선박 블록 납기기한 생성기")
        print("=" * 50)
        parser.print_help()
        print("\n💡 팁: 첫 번째 인자로 CSV 파일 경로를 제공해주세요.")
        return
    
    args = parser.parse_args()
    
    # 입력 파일 존재 확인
    if not Path(args.input_file).exists():
        print(f"❌ 오류: 입력 파일 '{args.input_file}'이 존재하지 않습니다.")
        return
    
    print("🚢 선박 블록 납기기한 생성기")
    print("=" * 50)
    print(f"📁 입력 파일: {args.input_file}")
    print(f"📅 기간: {args.start_date} ~ {args.end_date}")
    print(f"🎲 시드: {args.seed}")
    print()
    
    # 랜덤 시드 설정
    random.seed(args.seed)
    np.random.seed(args.seed)
    
    try:
        # 생성기 초기화
        generator = DeadlineGenerator(
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        # CSV 처리
        df, output_file = generator.process_csv(args.input_file, args.output_file)
        
        if df is not None:
            # 요약 보고서 생성
            generator.generate_summary_report(df, output_file)
            
            print(f"\n🎉 성공적으로 완료되었습니다!")
            print(f"📄 출력 파일: {output_file}")
            print(f"📋 요약 보고서: {Path(output_file).parent / f'{Path(output_file).stem}_report.txt'}")
            
            # 간단한 검증
            print(f"\n🔍 검증:")
            print(f"   - 모든 블록에 납기일 할당됨: {'✅' if df['deadline'].notna().all() else '❌'}")
            print(f"   - 납기일 범위 확인: {df['deadline'].min()} ~ {df['deadline'].max()}")
            
        else:
            print("❌ 처리 실패")
            
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")

if __name__ == "__main__":
    main()