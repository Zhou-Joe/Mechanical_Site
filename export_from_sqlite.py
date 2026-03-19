#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接读取SQLite数据库导出 Attraction 和 Equipment 数据
不需要Django环境，纯Python脚本

使用方法:
    python export_from_sqlite.py
"""

import json
import sqlite3
import os

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')
OUTPUT_FILE = 'attraction_equipment_data.json'


def export_data():
    """从SQLite数据库导出数据"""
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件不存在 - {DB_PATH}")
        return
    
    print(f"正在连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 导出 Attractions
    print("\n开始导出 Attractions...")
    attractions_data = []
    
    try:
        cursor.execute("""
            SELECT id, name, description, created_at, updated_at 
            FROM oil_records_attraction 
            ORDER BY id
        """)
        
        for row in cursor.fetchall():
            attraction_data = {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'] or '',
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }
            attractions_data.append(attraction_data)
            print(f"  - {row['name']}")
            
    except sqlite3.OperationalError as e:
        print(f"  错误: 无法读取 oil_records_attraction 表 - {e}")
    
    print(f"\n找到 {len(attractions_data)} 个 Attraction")
    
    # 导出 Equipments
    print("\n开始导出 Equipments...")
    equipments_data = []
    
    try:
        cursor.execute("""
            SELECT e.id, e.attraction_id, e.name, e.location, e.equipment_type,
                   e.created_at, e.updated_at, a.name as attraction_name
            FROM oil_records_equipment e
            LEFT JOIN oil_records_attraction a ON e.attraction_id = a.id
            ORDER BY e.id
        """)
        
        for row in cursor.fetchall():
            equipment_data = {
                'id': row['id'],
                'attraction_id': row['attraction_id'],
                'attraction_name': row['attraction_name'] or '',
                'name': row['name'],
                'location': row['location'] or '',
                'equipment_type': row['equipment_type'] or '',
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }
            equipments_data.append(equipment_data)
            print(f"  - {row['attraction_name']} - {row['name']}")
            
    except sqlite3.OperationalError as e:
        print(f"  错误: 无法读取 oil_records_equipment 表 - {e}")
    
    print(f"\n找到 {len(equipments_data)} 个 Equipment")
    
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
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"✓ 数据导出成功！")
    print(f"  文件: {output_path}")
    print(f"  Attraction 数量: {len(attractions_data)}")
    print(f"  Equipment 数量: {len(equipments_data)}")
    
    conn.close()


if __name__ == '__main__':
    export_data()
