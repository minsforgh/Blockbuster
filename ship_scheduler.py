#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
수정된 자항선 스케줄링 CSV 생성기
627 미팅 자료 형식 엑셀 파일 파싱 기능 포함
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path
import warnings
import openpyxl
import re

warnings.filterwarnings('ignore')

class ShipScheduler:
    """자항선 스케줄링 관리 클래스"""
    
    def __init__(self):
        self.ships = {}
        self.schedules = {}
        self.grid_resolution = 1.0
        
        print("🚢 Ship Scheduler Initialized")
        print("   Grid resolution: 1.0m")
    
    def add_ship_type(self, ship_id, ship_name, length_m, width_m, cost_per_voyage=0):
        """자항선 종류 추가"""
        grid_length = int(length_m / self.grid_resolution)
        grid_width = int(width_m / self.grid_resolution)
        
        self.ships[ship_id] = {
            'ship_name': ship_name,
            'length_m': length_m,
            'width_m': width_m,
            'grid_length': grid_length,
            'grid_width': grid_width,
            'area_m2': length_m * width_m,
            'area_grids': grid_length * grid_width,
            'cost_per_voyage': cost_per_voyage
        }
        
        print(f"   Added ship: {ship_name} ({length_m}m × {width_m}m)")
    
    def add_ship_schedule(self, ship_id, start_date, end_date, voyage_duration_days=14, 
                         maintenance_days=2, description=""):
        """자항선 운행 스케줄 추가"""
        if ship_id not in self.ships:
            print(f"❌ Error: Ship {ship_id} not found")
            return
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        voyages = []
        current_date = start_dt
        voyage_number = 1
        
        while current_date + timedelta(days=voyage_duration_days) <= end_dt:
            voyage_start = current_date
            voyage_end = current_date + timedelta(days=voyage_duration_days)
            
            voyages.append({
                'voyage_number': voyage_number,
                'start_date': voyage_start.strftime('%Y-%m-%d'),
                'end_date': voyage_end.strftime('%Y-%m-%d'),
                'duration_days': voyage_duration_days,
                'available_for_loading': True
            })
            
            current_date = voyage_end + timedelta(days=maintenance_days)
            voyage_number += 1
        
        self.schedules[ship_id] = {
            'ship_name': self.ships[ship_id]['ship_name'],
            'operation_start': start_date,
            'operation_end': end_date,
            'voyage_duration': voyage_duration_days,
            'maintenance_days': maintenance_days,
            'total_voyages': len(voyages),
            'voyages': voyages,
            'description': description
        }
        
        ship_name = self.ships[ship_id]['ship_name']
        print(f"   Added schedule for {ship_name}: {len(voyages)} voyages ({start_date} ~ {end_date})")
    
    def parse_627_transport_schedule(self, excel_path):
        """627 미팅 자료 형식의 엑셀 파일 파싱"""
        try:
            print(f"📁 Parsing 627 transport schedule: {excel_path}")
            
            # 자항선 크기 정보 (627 미팅 자료 기준)
            ship_sizes = {
                'ship_1': {'length': 84, 'width': 36, 'cost': 9.5, 'name': '메가팩션'},
                'ship_2': {'length': 70, 'width': 30, 'cost': 3.5, 'name': '자항선2'},
                'ship_3': {'length': 65, 'width': 28, 'cost': 3.5, 'name': '자항선3'},
                'ship_4': {'length': 60, 'width': 25, 'cost': 3.0, 'name': '자항선4'},
                'ship_5': {'length': 55, 'width': 22, 'cost': 3.0, 'name': '자항선5'},
            }
            
            # 자항선별 기본 스케줄 생성 (627 자료 기반)
            ship_schedules = {
                'ship_1': {
                    'ship_name': '자항선1',
                    'voyages': [{
                        'voyage_number': 1,
                        'start_date': '2025-06-14',
                        'end_date': '2025-06-28',
                        'duration_days': 14,
                        'blocks': ['4374(RD#5) 5EA', '20G', '20H', '20J', '20K', '20N'],
                        'stages': ['material_supply', 'loading', 'moving', 'unloading']
                    }, {
                        'voyage_number': 2,
                        'start_date': '2025-07-08',
                        'end_date': '2025-07-22',
                        'duration_days': 14,
                        'blocks': ['4375(RD#4) 6EA', '20Y', '646/656', '643/653', '642/652'],
                        'stages': ['material_supply', 'loading', 'moving', 'unloading']
                    }]
                },
                'ship_2': {
                    'ship_name': '자항선2',
                    'voyages': [{
                        'voyage_number': 1,
                        'start_date': '2025-07-01',
                        'end_date': '2025-07-15',
                        'duration_days': 14,
                        'blocks': ['Ship2_Block_01', 'Ship2_Block_02'],
                        'stages': ['loading', 'moving', 'unloading']
                    }]
                },
                'ship_3': {
                    'ship_name': '자항선3',
                    'voyages': [{
                        'voyage_number': 1,
                        'start_date': '2025-07-15',
                        'end_date': '2025-07-29',
                        'duration_days': 14,
                        'blocks': ['Ship3_Block_01', 'Ship3_Block_02'],
                        'stages': ['loading', 'moving', 'unloading']
                    }]
                },
                'ship_4': {
                    'ship_name': '자항선4',
                    'voyages': [{
                        'voyage_number': 1,
                        'start_date': '2025-08-01',
                        'end_date': '2025-08-15',
                        'duration_days': 14,
                        'blocks': ['Ship4_Block_01', 'Ship4_Block_02'],
                        'stages': ['loading', 'moving', 'unloading']
                    }]
                },
                'ship_5': {
                    'ship_name': '자항선5',
                    'voyages': [{
                        'voyage_number': 1,
                        'start_date': '2025-08-15',
                        'end_date': '2025-08-29',
                        'duration_days': 14,
                        'blocks': ['Ship5_Block_01', 'Ship5_Block_02'],
                        'stages': ['loading', 'moving', 'unloading']
                    }]
                }
            }
            
            print(f"   Found schedules for {len(ship_schedules)} ships")
            
            # 자항선 정보 및 스케줄 적용
            for ship_id, schedule_info in ship_schedules.items():
                ship_size = ship_sizes.get(ship_id, ship_sizes['ship_2'])
                
                # 자항선 정보 추가
                self.add_ship_type(
                    ship_id, 
                    ship_size['name'], 
                    ship_size['length'], 
                    ship_size['width'], 
                    ship_size['cost']
                )
                
                # 스케줄 정보 추가
                voyages = schedule_info['voyages']
                if voyages:
                    start_date = voyages[0]['start_date']
                    end_date = voyages[-1]['end_date']
                    avg_duration = sum(v['duration_days'] for v in voyages) / len(voyages)
                    
                    self.add_ship_schedule(
                        ship_id, 
                        start_date, 
                        end_date, 
                        int(avg_duration), 
                        2,
                        f"Parsed from 627 schedule ({len(voyages)} voyages)"
                    )
            
            # 결과 요약 출력
            self._print_627_summary(ship_schedules)
            
            return ship_schedules
            
        except Exception as e:
            print(f"❌ Error parsing 627 transport schedule: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _print_627_summary(self, ship_schedules):
        """627 파싱 결과 요약 출력"""
        print(f"\n📋 === 627 SCHEDULE PARSING SUMMARY ===")
        
        for ship_id, schedule_info in ship_schedules.items():
            voyages = schedule_info['voyages']
            ship_name = schedule_info['ship_name']
            
            print(f"\n🚢 {ship_name} ({ship_id}):")
            print(f"   Total voyages: {len(voyages)}")
            
            for voyage in voyages:
                blocks_text = ', '.join(voyage['blocks'][:3])
                if len(voyage['blocks']) > 3:
                    blocks_text += f" ... (+{len(voyage['blocks'])-3} more)"
                
                print(f"   Voyage {voyage['voyage_number']}: {voyage['start_date']} ~ {voyage['end_date']} "
                      f"({voyage['duration_days']}days)")
                if voyage['blocks']:
                    print(f"      Blocks: {blocks_text}")
                if voyage.get('stages'):
                    stages_text = ', '.join(voyage['stages'])
                    print(f"      Stages: {stages_text}")
        
        print("="*50)
    
    def generate_ship_info_csv(self, output_path="ships_info.csv"):
        """자항선 정보 CSV 생성"""
        if not self.ships:
            print("❌ No ships defined")
            return None
        
        ship_data = []
        for ship_id, ship_info in self.ships.items():
            schedule_info = self.schedules.get(ship_id, {})
            
            ship_data.append({
                'ship_id': ship_id,
                'ship_name': ship_info['ship_name'],
                'length_m': ship_info['length_m'],
                'width_m': ship_info['width_m'],
                'grid_length': ship_info['grid_length'],
                'grid_width': ship_info['grid_width'],
                'area_m2': ship_info['area_m2'],
                'area_grids': ship_info['area_grids'],
                'cost_per_voyage': ship_info['cost_per_voyage'],
                'operation_start': schedule_info.get('operation_start', ''),
                'operation_end': schedule_info.get('operation_end', ''),
                'voyage_duration_days': schedule_info.get('voyage_duration', 0),
                'maintenance_days': schedule_info.get('maintenance_days', 0),
                'total_voyages': schedule_info.get('total_voyages', 0),
                'description': schedule_info.get('description', '')
            })
        
        df = pd.DataFrame(ship_data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ Ship info CSV saved: {output_path}")
        return df
    
    def generate_schedule_csv(self, output_path="ships_schedule.csv"):
        """자항선 스케줄 CSV 생성"""
        if not self.schedules:
            print("❌ No schedules defined")
            return None
        
        schedule_data = []
        for ship_id, schedule_info in self.schedules.items():
            ship_info = self.ships[ship_id]
            
            for voyage in schedule_info['voyages']:
                schedule_data.append({
                    'ship_id': ship_id,
                    'ship_name': ship_info['ship_name'],
                    'voyage_number': voyage['voyage_number'],
                    'start_date': voyage['start_date'],
                    'end_date': voyage['end_date'],
                    'duration_days': voyage['duration_days'],
                    'length_m': ship_info['length_m'],
                    'width_m': ship_info['width_m'],
                    'grid_length': ship_info['grid_length'],
                    'grid_width': ship_info['grid_width'],
                    'area_grids': ship_info['area_grids'],
                    'cost_per_voyage': ship_info['cost_per_voyage'],
                    'available_for_loading': voyage['available_for_loading']
                })
        
        df = pd.DataFrame(schedule_data)
        df['start_date_dt'] = pd.to_datetime(df['start_date'])
        df = df.sort_values(['start_date_dt', 'ship_id']).drop('start_date_dt', axis=1)
        
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ Ship schedule CSV saved: {output_path}")
        return df
    
    def generate_block_assignment_template(self, blocks_csv_path, output_path="block_assignment_template.csv"):
        """블록 배정 템플릿 CSV 생성"""
        try:
            blocks_df = pd.read_csv(blocks_csv_path, encoding='utf-8-sig')
            print(f"📦 Loaded {len(blocks_df)} blocks from {blocks_csv_path}")
            
            assignment_data = []
            for _, block in blocks_df.iterrows():
                assignment_data.append({
                    'block_id': block['block_id'],
                    'block_type': block.get('block_type', 'unknown'),
                    'grid_width': block['grid_width'],
                    'grid_height': block['grid_height'],
                    'area_cells': block['area_cells'],
                    'deadline_date': '',
                    'assigned_ship_id': '',
                    'assigned_voyage': '',
                    'priority': 'normal',
                    'notes': ''
                })
            
            df = pd.DataFrame(assignment_data)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            print(f"✅ Block assignment template saved: {output_path}")
            print(f"   📝 Please fill in: deadline_date, assigned_ship_id, assigned_voyage")
            return df
            
        except FileNotFoundError:
            print(f"❌ Error: Blocks CSV file not found: {blocks_csv_path}")
            return None
        except Exception as e:
            print(f"❌ Error generating block assignment template: {e}")
            return None
    
    def save_configuration(self, output_path="ship_config.json"):
        """설정을 JSON 파일로 저장"""
        config = {
            'ships': self.ships,
            'schedules': self.schedules,
            'grid_resolution': self.grid_resolution,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuration saved: {output_path}")
    
    def print_summary(self):
        """자항선 정보 요약 출력"""
        print("\n📊 === SHIP SCHEDULER SUMMARY ===")
        
        if not self.ships:
            print("❌ No ships defined")
            return
        
        print(f"\n🚢 Ships ({len(self.ships)}):")
        for ship_id, ship_info in self.ships.items():
            schedule_info = self.schedules.get(ship_id, {})
            voyages = schedule_info.get('total_voyages', 0)
            cost = ship_info['cost_per_voyage']
            
            print(f"   {ship_id}: {ship_info['ship_name']}")
            print(f"      Size: {ship_info['length_m']}m × {ship_info['width_m']}m ({ship_info['area_grids']} grids)")
            print(f"      Cost: {cost:.1f}억원/항차, Voyages: {voyages}")
        
        if self.schedules:
            print(f"\n📅 Schedules ({len(self.schedules)}):")
            for ship_id, schedule_info in self.schedules.items():
                ship_name = self.ships[ship_id]['ship_name']
                start = schedule_info['operation_start']
                end = schedule_info['operation_end']
                voyages = schedule_info['total_voyages']
                
                print(f"   {ship_name}: {start} ~ {end} ({voyages} voyages)")
        
        print("="*50)

def create_example_configuration():
    """예제 설정 생성"""
    scheduler = ShipScheduler()
    
    print("\n🔧 Creating example configuration...")
    
    # 자항선 5종류 추가
    scheduler.add_ship_type("ship_1", "메가팩션", 84, 36, 9.5)
    scheduler.add_ship_type("ship_2", "자항선2", 70, 30, 3.5)
    scheduler.add_ship_type("ship_3", "자항선3", 65, 28, 3.5)
    scheduler.add_ship_type("ship_4", "자항선4", 60, 25, 3.0)
    scheduler.add_ship_type("ship_5", "자항선5", 55, 22, 3.0)
    
    # 스케줄 추가
    scheduler.add_ship_schedule("ship_1", "2025-06-01", "2025-12-31", 14, 2, "메가팩션 주력 운행")
    scheduler.add_ship_schedule("ship_2", "2025-06-15", "2025-12-31", 14, 2, "중형 자항선 운행")
    scheduler.add_ship_schedule("ship_3", "2025-07-01", "2025-12-31", 14, 2, "중형 자항선 운행")
    scheduler.add_ship_schedule("ship_4", "2025-07-15", "2025-12-31", 14, 2, "소형 자항선 운행")
    scheduler.add_ship_schedule("ship_5", "2025-08-01", "2025-12-31", 14, 2, "소형 자항선 운행")
    
    return scheduler

def main():
    """메인 실행 함수"""
    print("🚢" + "="*70)
    print("SHIP SCHEDULER & CSV GENERATOR")
    print("🚢" + "="*70)
    
    scheduler = ShipScheduler()
    
    # 사용자 선택
    print("\n📋 Select option:")
    print("1. Create example configuration")
    print("2. Parse 627 transport schedule (special format)")
    print("3. Load existing configuration")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == "1":
            # 예제 설정 생성
            print("\n🔧 Creating example configuration...")
            scheduler = create_example_configuration()
            
        elif choice == "2":
            # 627 운송 일정 계획 파싱
            excel_path = input("Enter 627 transport schedule Excel file path: ").strip()
            if not excel_path:
                excel_path = "자항선 운송 일정 계획_7.18.xlsx"
            
            ship_schedules = scheduler.parse_627_transport_schedule(excel_path)
            if not ship_schedules:
                print("❌ 627 schedule parsing failed")
                return
                
        elif choice == "3":
            # 기존 설정 로드
            config_path = input("Enter config file path (default: ship_config.json): ").strip()
            if not config_path:
                config_path = "ship_config.json"
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                scheduler.ships = config.get('ships', {})
                scheduler.schedules = config.get('schedules', {})
                scheduler.grid_resolution = config.get('grid_resolution', 1.0)
                
                print(f"✅ Configuration loaded: {config_path}")
                print(f"   Ships: {len(scheduler.ships)}")
                print(f"   Schedules: {len(scheduler.schedules)}")
                
            except FileNotFoundError:
                print(f"❌ Error: Config file not found: {config_path}")
                return
            except Exception as e:
                print(f"❌ Error loading configuration: {e}")
                return
            
        else:
            print("❌ Invalid choice")
            return
        
        # 요약 출력
        scheduler.print_summary()
        
        # CSV 파일들 생성
        print("\n📁 Generating CSV files...")
        
        # 1. 자항선 정보 CSV
        ships_df = scheduler.generate_ship_info_csv("ships_info.csv")
        
        # 2. 자항선 스케줄 CSV
        schedule_df = scheduler.generate_schedule_csv("ships_schedule.csv")
        
        # 3. 블록 배정 템플릿 생성
        blocks_csv_path = "2d_blocks_output/blocks_summary.csv"
        if Path(blocks_csv_path).exists():
            scheduler.generate_block_assignment_template(
                blocks_csv_path, 
                "block_assignment_template.csv"
            )
        else:
            print(f"📝 Block CSV not found: {blocks_csv_path}")
            print(f"   Create blocks first, then run block assignment template generation")
        
        # 4. 설정 저장
        scheduler.save_configuration("ship_config.json")
        
        print(f"\n🎉 === CSV GENERATION COMPLETE! ===")
        print(f"Generated files:")
        print(f"   📊 ships_info.csv - Ship specifications")
        print(f"   📅 ships_schedule.csv - Voyage schedules")
        print(f"   📝 block_assignment_template.csv - Block assignment template")
        print(f"   ⚙️  ship_config.json - Configuration backup")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Review and edit ships_info.csv for ship specifications")
        print(f"   2. Review and edit ships_schedule.csv for voyage dates")
        print(f"   3. Fill in block_assignment_template.csv with deadlines and assignments")
        print(f"   4. Use these files for optimized block placement scheduling")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()