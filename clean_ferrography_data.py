#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
清理所有铁谱报告数据
"""

import sqlite3

DB_PATH = 'c:\\Users\\czhou7\\PythonProjects\\Oil\\db.sqlite3'

def clean_all_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("清理铁谱报告所有数据...")
    
    # 删除所有数据
    tables = [
        'ferrography_reports_ferrographyparticle',
        'ferrography_reports_ferrographydiagnosis',
        'ferrography_reports_ferrographyreport',
    ]
    
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        print(f"✅ 已清理表: {table}")
    
    # 重置自增ID
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
            print(f"✅ 已重置自增ID: {table}")
        except:
            pass
    
    conn.commit()
    conn.close()
    
    print("\n✅ 所有数据清理完成!")

if __name__ == '__main__':
    clean_all_data()
