#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 JSON 文件导入 Attraction 和 Equipment 数据到新环境

使用方法:
    python manage.py import_attraction_equipment --input=attraction_equipment_data.json
    
可选参数:
    --clear: 导入前清空现有数据
    --skip-existing: 跳过已存在的记录（根据name判断）
"""

import json
from django.core.management.base import BaseCommand
from oil_records.models import Attraction, Equipment


class Command(BaseCommand):
    help = '从 JSON 文件导入 Attraction 和 Equipment 数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            default='attraction_equipment_data.json',
            help='输入文件路径 (默认: attraction_equipment_data.json)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='导入前清空现有数据'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='跳过已存在的记录（根据name判断）'
        )

    def handle(self, *args, **options):
        input_file = options['input']
        clear_data = options['clear']
        skip_existing = options['skip_existing']
        
        self.stdout.write(self.style.NOTICE('开始导入 Attraction 和 Equipment 数据...'))
        
        # 读取 JSON 文件
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'错误: 文件不存在 - {input_file}'))
            return
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'错误: JSON 格式错误 - {e}'))
            return
        
        # 验证数据格式
        if 'attractions' not in data or 'equipments' not in data:
            self.stdout.write(self.style.ERROR('错误: 数据格式不正确，缺少 attractions 或 equipments 字段'))
            return
        
        attractions_data = data.get('attractions', [])
        equipments_data = data.get('equipments', [])
        
        self.stdout.write(f'  文件信息: {data.get("meta", {})}')
        self.stdout.write(f'  待导入 Attraction: {len(attractions_data)}')
        self.stdout.write(f'  待导入 Equipment: {len(equipments_data)}')
        
        # 清空现有数据（如果指定了 --clear）
        if clear_data:
            self.stdout.write(self.style.WARNING('\n警告: 正在清空现有数据...'))
            Equipment.objects.all().delete()
            Attraction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  现有数据已清空'))
        
        # 导入 Attractions
        self.stdout.write('\n开始导入 Attractions...')
        attraction_id_map = {}  # 用于映射旧ID到新对象
        created_count = 0
        skipped_count = 0
        
        for attr_data in attractions_data:
            name = attr_data['name']
            
            # 检查是否已存在
            existing = Attraction.objects.filter(name=name).first()
            if existing:
                if skip_existing:
                    self.stdout.write(f'  跳过已存在的 Attraction: {name}')
                    attraction_id_map[attr_data['id']] = existing
                    skipped_count += 1
                    continue
                else:
                    self.stdout.write(f'  更新 Attraction: {name}')
                    existing.description = attr_data.get('description', '')
                    existing.save()
                    attraction_id_map[attr_data['id']] = existing
                    continue
            
            # 创建新记录
            attraction = Attraction.objects.create(
                name=name,
                description=attr_data.get('description', ''),
            )
            attraction_id_map[attr_data['id']] = attraction
            created_count += 1
            self.stdout.write(f'  创建 Attraction: {name}')
        
        self.stdout.write(self.style.SUCCESS(f'  Attraction 导入完成: 创建 {created_count}, 跳过 {skipped_count}'))
        
        # 导入 Equipments
        self.stdout.write('\n开始导入 Equipments...')
        created_count = 0
        skipped_count = 0
        failed_count = 0
        
        for eq_data in equipments_data:
            name = eq_data['name']
            old_attraction_id = eq_data['attraction_id']
            attraction_name = eq_data.get('attraction_name', '')
            
            # 获取对应的 Attraction
            attraction = attraction_id_map.get(old_attraction_id)
            if not attraction:
                self.stdout.write(self.style.ERROR(
                    f'  错误: 找不到 Equipment "{name}" 对应的 Attraction (ID: {old_attraction_id}, 名称: {attraction_name})'
                ))
                failed_count += 1
                continue
            
            # 检查是否已存在（同一attraction下同名equipment）
            existing = Equipment.objects.filter(
                attraction=attraction,
                name=name
            ).first()
            
            if existing:
                if skip_existing:
                    self.stdout.write(f'  跳过已存在的 Equipment: {attraction.name} - {name}')
                    skipped_count += 1
                    continue
                else:
                    self.stdout.write(f'  更新 Equipment: {attraction.name} - {name}')
                    existing.location = eq_data.get('location', '')
                    existing.equipment_type = eq_data.get('equipment_type', '')
                    existing.save()
                    continue
            
            # 创建新记录
            Equipment.objects.create(
                attraction=attraction,
                name=name,
                location=eq_data.get('location', ''),
                equipment_type=eq_data.get('equipment_type', ''),
            )
            created_count += 1
            self.stdout.write(f'  创建 Equipment: {attraction.name} - {name}')
        
        self.stdout.write(self.style.SUCCESS(f'  Equipment 导入完成: 创建 {created_count}, 跳过 {skipped_count}, 失败 {failed_count}'))
        
        # 最终统计
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('✓ 数据导入完成！'))
        self.stdout.write(f'  当前 Attraction 总数: {Attraction.objects.count()}')
        self.stdout.write(f'  当前 Equipment 总数: {Equipment.objects.count()}')
