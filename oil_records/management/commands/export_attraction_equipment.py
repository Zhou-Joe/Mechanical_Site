#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出 Attraction 和 Equipment 数据到 JSON 文件
用于迁移到新环境时保留基础数据

使用方法:
    python manage.py export_attraction_equipment --output=attraction_equipment_data.json
"""

import json
from django.core.management.base import BaseCommand
from oil_records.models import Attraction, Equipment


class Command(BaseCommand):
    help = '导出 Attraction 和 Equipment 数据到 JSON 文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='attraction_equipment_data.json',
            help='输出文件路径 (默认: attraction_equipment_data.json)'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        
        self.stdout.write(self.style.NOTICE('开始导出 Attraction 和 Equipment 数据...'))
        
        # 导出 Attractions
        attractions_data = []
        attractions = Attraction.objects.all().order_by('id')
        
        for attraction in attractions:
            attraction_data = {
                'id': attraction.id,
                'name': attraction.name,
                'description': attraction.description,
                'created_at': attraction.created_at.isoformat() if attraction.created_at else None,
                'updated_at': attraction.updated_at.isoformat() if attraction.updated_at else None,
            }
            attractions_data.append(attraction_data)
        
        self.stdout.write(f'  - 找到 {len(attractions_data)} 个 Attraction')
        
        # 导出 Equipments
        equipments_data = []
        equipments = Equipment.objects.all().select_related('attraction').order_by('id')
        
        for equipment in equipments:
            equipment_data = {
                'id': equipment.id,
                'attraction_id': equipment.attraction.id,
                'attraction_name': equipment.attraction.name,  # 用于参考和验证
                'name': equipment.name,
                'location': equipment.location,
                'equipment_type': equipment.equipment_type,
                'created_at': equipment.created_at.isoformat() if equipment.created_at else None,
                'updated_at': equipment.updated_at.isoformat() if equipment.updated_at else None,
            }
            equipments_data.append(equipment_data)
        
        self.stdout.write(f'  - 找到 {len(equipments_data)} 个 Equipment')
        
        # 组装完整数据
        export_data = {
            'meta': {
                'version': '1.0',
                'source': 'oil_records_export',
                'total_attractions': len(attractions_data),
                'total_equipments': len(equipments_data),
            },
            'attractions': attractions_data,
            'equipments': equipments_data,
        }
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ 数据导出成功！'))
        self.stdout.write(f'  文件: {output_file}')
        self.stdout.write(f'  Attraction 数量: {len(attractions_data)}')
        self.stdout.write(f'  Equipment 数量: {len(equipments_data)}')
