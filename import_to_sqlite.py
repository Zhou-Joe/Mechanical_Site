#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接导入 Attraction 和 Equipment 数据到 SQLite 数据库
不需要Django环境，纯Python脚本

使用方法:
    python import_to_sqlite.py --input=attraction_equipment_data.json

可选参数:
    --clear: 导入前清空现有数据
    --skip-existing: 跳过已存在的记录
"""

import json
import sqlite3
import os
import argparse

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db.sqlite3')
DEFAULT_INPUT = 'attraction_equipment_data.json'


def import_data(input_file, clear_data=False, skip_existing=False):
    """导入数据到SQLite数据库"""
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在 - {input_file}")
        return
    
    if not os.path.exists(DB_PATH):
        print(f"错误: 数据库文件不存在 - {DB_PATH}")
        print("请确保已经运行了 Django 迁移命令: python manage.py migrate")
        return
    
    # 读取 JSON 文件
    print(f"正在读取数据文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    attractions_data = data.get('attractions', [])
    equipments_data = data.get('equipments', [])
    
    print(f"  待导入 Attraction: {len(attractions_data)}")
    print(f"  待导入 Equipment: {len(equipments_data)}")
    
    # 连接数据库
    print(f"\n正在连接数据库: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 清空现有数据（如果指定了 --clear）
    if clear_data:
        print("\n警告: 正在清空现有数据...")
        cursor.execute("DELETE FROM oil_records_equipment")
        cursor.execute("DELETE FROM oil_records_attraction")
        conn.commit()
        print("  现有数据已清空")
    
    # 导入 Attractions
    print("\n开始导入 Attractions...")
    attraction_id_map = {}  # 用于映射旧ID到新ID
    created_count = 0
    skipped_count = 0
    
    for attr_data in attractions_data:
        name = attr_data['name']
        old_id = attr_data['id']
        
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM oil_records_attraction WHERE name = ?",
            (name,)
        )
        existing = cursor.fetchone()
        
        if existing:
            if skip_existing:
                print(f"  跳过已存在的 Attraction: {name}")
                attraction_id_map[old_id] = existing[0]
                skipped_count += 1
                continue
            else:
                print(f"  更新 Attraction: {name}")
                cursor.execute(
                    """UPDATE oil_records_attraction 
                       SET description = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    (attr_data.get('description', ''), existing[0])
                )
                attraction_id_map[old_id] = existing[0]
                continue
        
        # 创建新记录
        cursor.execute(
            """INSERT INTO oil_records_attraction (name, description, created_at, updated_at)
               VALUES (?, ?, datetime('now'), datetime('now'))""",
            (name, attr_data.get('description', ''))
        )
        new_id = cursor.lastrowid
        attraction_id_map[old_id] = new_id
        created_count += 1
        print(f"  创建 Attraction: {name} (ID: {new_id})")
    
    conn.commit()
    print(f"  Attraction 导入完成: 创建 {created_count}, 跳过 {skipped_count}")
    
    # 导入 Equipments
    print("\n开始导入 Equipments...")
    created_count = 0
    skipped_count = 0
    failed_count = 0
    
    for eq_data in equipments_data:
        name = eq_data['name']
        old_attraction_id = eq_data['attraction_id']
        attraction_name = eq_data.get('attraction_name', '')
        
        # 获取对应的 Attraction ID
        new_attraction_id = attraction_id_map.get(old_attraction_id)
        if not new_attraction_id:
            print(f"  错误: 找不到 Equipment \"{name}\" 对应的 Attraction (ID: {old_attraction_id}, 名称: {attraction_name})")
            failed_count += 1
            continue
        
        # 检查是否已存在（同一attraction下同名equipment）
        cursor.execute(
            """SELECT id FROM oil_records_equipment 
               WHERE attraction_id = ? AND name = ?""",
            (new_attraction_id, name)
        )
        existing = cursor.fetchone()
        
        if existing:
            if skip_existing:
                print(f"  跳过已存在的 Equipment: {attraction_name} - {name}")
                skipped_count += 1
                continue
            else:
                print(f"  更新 Equipment: {attraction_name} - {name}")
                cursor.execute(
                    """UPDATE oil_records_equipment 
                       SET location = ?, equipment_type = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    (eq_data.get('location', ''), eq_data.get('equipment_type', ''), existing[0])
                )
                continue
        
        # 创建新记录
        cursor.execute(
            """INSERT INTO oil_records_equipment 
               (attraction_id, name, location, equipment_type, created_at, updated_at)
               VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (new_attraction_id, name, eq_data.get('location', ''), eq_data.get('equipment_type', ''))
        )
        created_count += 1
        print(f"  创建 Equipment: {attraction_name} - {name}")
    
    conn.commit()
    print(f"  Equipment 导入完成: 创建 {created_count}, 跳过 {skipped_count}, 失败 {failed_count}")
    
    # 最终统计
    cursor.execute("SELECT COUNT(*) FROM oil_records_attraction")
    total_attractions = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM oil_records_equipment")
    total_equipments = cursor.fetchone()[0]
    
    print(f"\n{'='*50}")
    print(f"✓ 数据导入完成！")
    print(f"  当前 Attraction 总数: {total_attractions}")
    print(f"  当前 Equipment 总数: {total_equipments}")
    
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='导入 Attraction 和 Equipment 数据到 SQLite 数据库')
    parser.add_argument(
        '--input',
        type=str,
        default=DEFAULT_INPUT,
        help=f'输入文件路径 (默认: {DEFAULT_INPUT})'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='导入前清空现有数据'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='跳过已存在的记录'
    )
    
    args = parser.parse_args()
    import_data(args.input, args.clear, args.skip_existing)
