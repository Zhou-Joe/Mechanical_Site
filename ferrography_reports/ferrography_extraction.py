"""
铁谱报告数据提取和匹配模块
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime


def extract_ferrography_data(md_content: str) -> Dict[str, Any]:
    """
    从OCR生成的Markdown内容中提取铁谱分析数据
    
    Args:
        md_content: OCR生成的Markdown文本
        
    Returns:
        包含提取数据的字典
    """
    data = {
        'report_date': None,
        'sample_date': None,
        'report_number': None,
        'particles': [],
        'diagnosis': {
            'overall_assessment': '',
            'wear_status': '',
            'recommendations': ''
        }
    }
    
    if not md_content:
        return data
    
    # 提取报告日期
    date_patterns = [
        r'报告日期[:：]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'日期[:：]\s*(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})\s*报告',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, md_content)
        if match:
            data['report_date'] = match.group(1).replace('/', '-')
            break
    
    # 提取报告编号
    number_patterns = [
        r'报告编号[:：]\s*([A-Za-z0-9\-]+)',
        r'编号[:：]\s*([A-Za-z0-9\-]+)',
        r'No\.?\s*[:：]?\s*([A-Za-z0-9\-]+)',
    ]
    
    for pattern in number_patterns:
        match = re.search(pattern, md_content)
        if match:
            data['report_number'] = match.group(1)
            break
    
    # 提取磨损颗粒类型和严重等级
    particle_types = [
        ('正常磨损磨粒', 'normal'),
        ('切削磨损颗粒', 'cutting'),
        ('严重滑动磨损颗粒', 'severe_sliding'),
        ('滚动疲劳磨损颗粒', 'rolling_fatigue'),
        ('滚/滑齿轮磨损颗粒', 'gear'),
        ('腐蚀磨损颗粒', 'corrosion'),
        ('黑色氧化物', 'black_oxide'),
        ('红色氧化物', 'red_oxide'),
        ('有色金属磨损颗粒', 'non_ferrous'),
        ('灰尘/氧化皮', 'dust'),
        ('油变质产物', 'oil_degradation'),
        ('纤维/漆', 'fiber'),
        ('其它污染物', 'contaminant'),
    ]
    
    # 严重等级映射
    severity_map = {
        '无': 'none',
        '少量': 'low',
        '中等': 'medium',
        '大量': 'high',
    }
    
    for particle_name, particle_key in particle_types:
        # 查找颗粒类型行
        pattern = rf'{particle_name}\s*([✓✔√■●◆☑]?)\s*(\d*)'
        match = re.search(pattern, md_content)
        
        if match:
            has_mark = match.group(1) != ''
            size = match.group(2) if match.group(2) else ''
            
            # 确定严重等级
            severity = 'low' if has_mark else 'none'
            
            particle_data = {
                'type': particle_name,
                'type_key': particle_key,
                'severity': severity,
                'size': size,
                'detected': has_mark
            }
            data['particles'].append(particle_data)
    
    # 提取诊断结论
    # 查找总体评价/诊断建议部分
    diagnosis_patterns = [
        r'总体评价[:：]\s*(.+?)(?=\n\s*#|\n\s*分析|$)',
        r'诊断建议[:：]\s*(.+?)(?=\n\s*#|\n\s*分析|$)',
        r'诊断结论[:：]\s*(.+?)(?=\n\s*#|\n\s*分析|$)',
        r'结论[:：]\s*(.+?)(?=\n\s*#|\n\s*分析|$)',
    ]
    
    for pattern in diagnosis_patterns:
        match = re.search(pattern, md_content, re.DOTALL)
        if match:
            conclusion = match.group(1).strip()
            # 清理结论文本
            conclusion = re.sub(r'!\[.*?\]\(.*?\)', '', conclusion)  # 移除图片
            conclusion = re.sub(r'\n+', ' ', conclusion)  # 合并换行
            conclusion = conclusion.strip()
            
            if conclusion:
                data['diagnosis']['overall_assessment'] = conclusion
                break
    
    # 提取磨损状态
    wear_status_patterns = [
        r'磨损状态[:：]\s*(.+)',
        r'磨损[:：]\s*(.+)',
    ]
    
    for pattern in wear_status_patterns:
        match = re.search(pattern, md_content)
        if match:
            data['diagnosis']['wear_status'] = match.group(1).strip()
            break
    
    # 提取建议措施
    recommendation_patterns = [
        r'建议措施[:：]\s*(.+?)(?=\n\s*#|$)',
        r'建议[:：]\s*(.+?)(?=\n\s*#|$)',
    ]
    
    for pattern in recommendation_patterns:
        match = re.search(pattern, md_content, re.DOTALL)
        if match:
            data['diagnosis']['recommendations'] = match.group(1).strip()
            break
    
    return data


def match_ferrography_equipment(filename: str) -> Dict[str, Any]:
    """
    根据文件名匹配铁谱检测设备和景点
    
    Args:
        filename: PDF文件名
        
    Returns:
        匹配后的设备信息
    """
    import sqlite3
    
    DB_PATH = 'c:\\Users\\czhou7\\PythonProjects\\Oil\\db.sqlite3'
    equipment_info = {
        'matched_attraction_id': None,
        'matched_equipment_id': None,
        'matched_attraction_name': None,
        'matched_equipment_name': None,
    }
    
    # 处理文件名：统一格式
    # 1. 转换为小写
    search_text = filename.lower()
    # 2. 移除所有空格、横线、下划线、括号等特殊字符
    search_text = re.sub(r'[\s\-_\(\)\[\]\{\}#]', '', search_text)
    # 3. 移除.pdf后缀
    search_text = search_text.replace('.pdf', '')
    
    print(f"铁谱报告 - 原始文件名: {repr(filename)}")
    print(f"铁谱报告 - 处理后搜索文本: {repr(search_text)}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 匹配景点
    matched_attraction_id = None
    matched_attraction_name = None
    
    # 硬编码匹配景点
    if '举起' in search_text or 'soaring' in search_text:
        matched_attraction_name = 'Soaring'
    elif 'hps' in search_text:
        matched_attraction_name = 'HPS'
    elif 'dumbo' in search_text:
        matched_attraction_name = 'Dumbo'
    elif 'jetpack' in search_text:
        matched_attraction_name = 'Jetpack'
    elif 'carousel' in search_text:
        matched_attraction_name = 'Carousel'
    
    if not matched_attraction_name:
        print(f"⚠️ 未能从文件名识别景点")
        conn.close()
        return equipment_info
    
    print(f"✅ 匹配到景点: {matched_attraction_name}")
    
    # 查询景点ID
    cursor.execute(
        "SELECT id FROM ferrography_reports_ferrographyattraction WHERE name = ?",
        (matched_attraction_name,)
    )
    result = cursor.fetchone()
    if not result:
        print(f"❌ 数据库中未找到景点: {matched_attraction_name}")
        conn.close()
        return equipment_info
    
    matched_attraction_id = result[0]
    equipment_info['matched_attraction_id'] = matched_attraction_id
    equipment_info['matched_attraction_name'] = matched_attraction_name
    
    # 匹配设备
    matched_equipment_id = None
    matched_equipment_name = None
    
    # 1. 匹配Soaring设备
    if matched_attraction_name == 'Soaring':
        print(f"🔍 尝试匹配举起设备...")
        
        # 匹配马达轴承设备 (AA前端, BB后端等)
        motor_bearing_codes = ['AA', 'AB', 'AC', 'BA', 'BB', 'BC']
        positions = ['前端', '后端']
        
        for code in motor_bearing_codes:
            for position in positions:
                pattern = f'{code}{position}'.lower()
                if pattern in search_text:
                    equip_name = f'马达轴承 - {code}{position}'
                    print(f"  ✅ 找到设备模式: {equip_name}")
                    
                    cursor.execute(
                        """SELECT id, name FROM ferrography_reports_ferrographyequipment 
                           WHERE attraction_id = ? AND name = ?""",
                        (matched_attraction_id, equip_name)
                    )
                    result = cursor.fetchone()
                    if result:
                        matched_equipment_id, matched_equipment_name = result
                        print(f"  ✅ 匹配到设备: {matched_equipment_name}")
                        break
                    else:
                        print(f"  ❌ 数据库中未找到设备: {equip_name}")
            
            if matched_equipment_id:
                break
        
        if not matched_equipment_id:
            print(f"⚠️ 未匹配到具体设备")
    
    # 2. 匹配HPS转盘设备
    if not matched_equipment_id and matched_attraction_name == 'HPS':
        print(f"🔍 尝试匹配HPS设备...")
        
        hps_equipments = ['大转盘', '小转盘1', '小转盘2', '小转盘3', '小转盘4']
        
        for equip_name in hps_equipments:
            # 简化匹配
            simple_name = equip_name.replace('小转盘', '小转盘')
            if simple_name in search_text or equip_name.replace('转盘', '').lower() in search_text:
                print(f"  ✅ 找到设备: {equip_name}")
                
                cursor.execute(
                    """SELECT id, name FROM ferrography_reports_ferrographyequipment 
                       WHERE attraction_id = ? AND name = ?""",
                    (matched_attraction_id, equip_name)
                )
                result = cursor.fetchone()
                if result:
                    matched_equipment_id, matched_equipment_name = result
                    print(f"  ✅ 匹配到设备: {matched_equipment_name}")
                    break
    
    # 3. 匹配其他设备 (Dumbo, Jetpack, Carousel)
    if not matched_equipment_id:
        print(f"🔍 尝试匹配其他设备...")
        
        # 获取该景点的所有设备
        cursor.execute(
            """SELECT id, name FROM ferrography_reports_ferrographyequipment 
               WHERE attraction_id = ? ORDER BY name""",
            (matched_attraction_id,)
        )
        equipments = cursor.fetchall()
        
        for equip_id, equip_name in equipments:
            # 简化设备名进行匹配
            simple_equip_name = equip_name.replace('轴承油脂', '').replace(' ', '').lower()
            
            # 多种匹配方式
            match_patterns = [
                simple_equip_name,  # 简化后的设备名
                equip_name.lower(),  # 完整设备名小写
                equip_name.lower().replace('轴承油脂', '轴承'),  # 替换轴承油脂
            ]
            
            matched = False
            for pattern in match_patterns:
                if pattern in search_text:
                    matched = True
                    break
            
            # 特殊处理：Carousel的大转盘#1, #2等
            if not matched and matched_attraction_name == 'Carousel':
                if '大转盘' in equip_name and '大转盘' in search_text:
                    # 检查是否有#1, #2等编号
                    if '#1' in filename and equip_name == '大转盘':
                        matched = True
                    elif '#2' in filename and equip_name == '大转盘':
                        matched = True
                    elif '#1' not in filename and '#2' not in filename and equip_name == '大转盘':
                        matched = True
            
            if matched:
                matched_equipment_id = equip_id
                matched_equipment_name = equip_name
                print(f"  ✅ 匹配到设备: {matched_equipment_name}")
                break
    
    if matched_equipment_id:
        equipment_info['matched_equipment_id'] = matched_equipment_id
        equipment_info['matched_equipment_name'] = matched_equipment_name
    else:
        print(f"⚠️ 未匹配到具体设备，但已匹配景点: {matched_attraction_name}")
    
    conn.close()
    return equipment_info


def find_or_create_ferrography_equipment(equipment_info: Dict[str, Any]) -> tuple:
    """
    查找或创建铁谱报告设备
    
    Returns:
        (equipment_id, equipment_name) 元组
    """
    if equipment_info.get('matched_equipment_id'):
        return equipment_info['matched_equipment_id'], equipment_info.get('matched_equipment_name', '')
    
    if equipment_info.get('matched_attraction_id'):
        # 返回景点ID，设备待手动选择
        return None, None
    
    return None, None


# 兼容旧版本的函数名
def match_equipment_for_ferrography(equipment_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """
    兼容旧版本的设备匹配函数
    
    Args:
        equipment_data: 设备信息字典（旧版本使用，现在忽略）
        filename: PDF文件名
        
    Returns:
        匹配后的设备信息（包含 matched_equipment, matched_attraction 对象）
    """
    import sqlite3
    
    # 调用新的匹配函数
    result = match_ferrography_equipment(filename)
    
    # 查询完整的对象信息
    DB_PATH = 'c:\\Users\\czhou7\\PythonProjects\\Oil\\db.sqlite3'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 添加设备对象信息（用于兼容旧代码）
    if result.get('matched_equipment_id'):
        cursor.execute(
            "SELECT name FROM ferrography_reports_ferrographyequipment WHERE id = ?",
            (result['matched_equipment_id'],)
        )
        row = cursor.fetchone()
        if row:
            # 创建一个简单的对象模拟
            result['matched_equipment'] = type('Equipment', (), {'id': result['matched_equipment_id'], 'name': row[0]})()
    
    if result.get('matched_attraction_id'):
        cursor.execute(
            "SELECT name FROM ferrography_reports_ferrographyattraction WHERE id = ?",
            (result['matched_attraction_id'],)
        )
        row = cursor.fetchone()
        if row:
            result['matched_attraction'] = type('Attraction', (), {'id': result['matched_attraction_id'], 'name': row[0]})()
    
    conn.close()
    
    return result
