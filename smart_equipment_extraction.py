"""
智能设备信息提取模块
从PDF文件名和OCR内容中自动提取设备信息
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

def extract_equipment_info(md_content: str, filename: str = "") -> Dict[str, any]:
    """
    从MD内容和文件名中提取设备信息
    
    Args:
        md_content: OCR处理后的MD内容
        filename: PDF文件名
        
    Returns:
        包含设备信息的字典
    """
    equipment_info = {
        'equipment_name': '',
        'location': '',
        'equipment_type': '',
        'extraction_method': '',
        'raw_matches': []
    }
    
    # 1. 从文件名提取设备信息
    filename_info = extract_from_filename(filename)
    if filename_info.get('equipment_name') or filename_info.get('location') or filename_info.get('equipment_type'):
        equipment_info.update(filename_info)
        equipment_info['extraction_method'] = 'filename'
    
    # 2. 从MD内容提取设备信息
    md_info = extract_from_md_content(md_content)
    if md_info.get('equipment_name') or md_info.get('location') or md_info.get('equipment_type'):
        equipment_info.update(md_info)
        if not equipment_info.get('extraction_method'):
            equipment_info['extraction_method'] = 'md_content'
    
    return equipment_info

def extract_from_filename(filename: str) -> Dict[str, any]:
    """从文件名提取设备信息"""
    if not filename:
        return {'equipment_name': '', 'location': '', 'equipment_type': ''}
    
    filename = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
    
    result = {
        'equipment_name': '',
        'location': '',
        'equipment_type': ''
    }
    
    filename_lower = filename.lower()
    
    # 直接硬编码匹配游乐设施名称
    if 'rapids' in filename_lower or '激流' in filename_lower:
        result['equipment_name'] = 'Rapids'
    elif 'soaring' in filename_lower or '飞翔' in filename_lower:
        result['equipment_name'] = 'SOARING'
    elif 'dumbo' in filename_lower or '小飞象' in filename_lower:
        result['equipment_name'] = 'Dumbo'
    elif 'carousel' in filename_lower or '旋转木马' in filename_lower:
        result['equipment_name'] = 'Carousel'
    elif 'jetpack' in filename_lower or '喷气' in filename_lower:
        result['equipment_name'] = 'Jetpack'
    elif 'mine' in filename_lower or 'train' in filename_lower or '矿山' in filename_lower:
        result['equipment_name'] = 'Mine Train'
    elif 'slinky' in filename_lower or '弹簧' in filename_lower:
        result['equipment_name'] = 'Slinky'
    elif 'woody' in filename_lower or '胡迪' in filename_lower:
        result['equipment_name'] = 'Woody'
    elif 'tron' in filename_lower:
        result['equipment_name'] = 'Tron'
    elif 'hps' in filename_lower or '罐' in filename_lower:
        result['equipment_name'] = 'HPS'
    
    # 直接硬编码匹配设备类型
    if 'gearbox' in filename_lower or '齿轮箱' in filename_lower:
        result['equipment_type'] = '齿轮箱'
    elif 'drive' in filename_lower or '驱动' in filename_lower:
        result['equipment_type'] = '驱动'
    elif 'lift' in filename_lower or '提升' in filename_lower:
        result['equipment_type'] = '提升'
    
    # 直接硬编码匹配位置
    if 'left' in filename_lower or '左' in filename_lower:
        result['location'] = '左'
    elif 'right' in filename_lower or '右' in filename_lower:
        result['location'] = '右'
    elif 'front' in filename_lower or '前' in filename_lower:
        result['location'] = '前'
    elif 'rear' in filename_lower or '后' in filename_lower:
        result['location'] = '后'
    
    # 提取编号信息
    number_match = re.search(r'(\d+)', filename)
    if number_match:
        number = number_match.group(1)
        if result['equipment_name']:
            result['equipment_name'] += f" #{number}"
        else:
            result['equipment_name'] = f"设备 #{number}"
    
    return result

def extract_from_md_content(md_content: str) -> Dict[str, any]:
    """从MD内容提取设备信息"""
    if not md_content:
        return {'equipment_name': '', 'location': '', 'equipment_type': ''}
    
    result = {
        'equipment_name': '',
        'location': '',
        'equipment_type': '',
        'raw_matches': []
    }
    
    # 先清理MD内容，移除HTML表格标签
    cleaned_content = md_content
    # 移除HTML表格标签
    cleaned_content = re.sub(r'<[^>]+>', ' ', cleaned_content)
    # 移除多余的空白字符
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
    
    # 常见的设备信息模式 - 更严格的匹配
    patterns = [
        # 设备名称模式 - 排除ADMINISTRATION等无关词汇和HTML标签
        (r'(?:设备名称|设备|Equipment|设备编号)[:：]\s*([A-Za-z0-9\u4e00-\u9fff\s#]+)', 'equipment_name'),
        # 更严格的设备名称模式，排除常见无关词汇
        (r'(?!ADMINISTRATION|CUSTOMER|CURRENT|DIAGNOSIS|Results|Graphs|table|td|tr)([A-Z][a-zA-Z\u4e00-\u9fff]+\s*(?:Gearbox|Kicker|Wheel|Lift|Drive)[\s\d#]*)', 'equipment_name'),
        # 位置模式 - 只匹配中文或英文位置
        (r'(?:位置|Location|安装位置)[:：]\s*([左|右|前|后|Left|Right|Front|Rear]+)', 'location'),
        # 设备类型模式
        (r'(?:设备类型|Type|类型)[:：]\s*([A-Za-z0-9\u4e00-\u9fff\s]+)', 'equipment_type')
    ]
    
    for pattern, field_name in patterns:
        matches = re.findall(pattern, cleaned_content, re.IGNORECASE)
        for match in matches:
            match = match.strip()
            # 验证匹配结果的有效性
            if match and len(match) < 50 and not any(char in match for char in ['<', '>', '=', 'td', 'tr', 'rowspan', 'colspan']):
                if not result[field_name]:
                    result[field_name] = match
                    result['raw_matches'].append({'field': field_name, 'value': match, 'source': 'md_content'})
    
    return result

def simple_match_equipment(equipment_info: Dict[str, any], filename: str = "") -> Dict[str, any]:
    """
    简单粗暴的硬编码匹配方法：
    1. 硬编码匹配8个景点：rapids, mine train, slinky, dumbo, carousel, tron, jetpack, soaring
    2. 如果匹配到mine train，进一步匹配lift A或lift B
    3. 其他景点直接匹配设备
    
    Args:
        equipment_info: 已提取的设备信息
        filename: PDF文件名
        
    Returns:
        匹配后的设备信息
    """
    from oil_records.models import Attraction, Equipment
    
    # 准备搜索文本
    search_text = (filename).lower()
    
    print(f"搜索文本: {search_text}")
    
    matched_attraction_name = None
    
    print("\n=== 硬编码匹配景点 ===")
    # 直接硬编码匹配景点，不用keywords
    # 首先检查马达轴承（特殊处理：文件名不含soaring但属于soaring景点）
    if '马达轴承' in search_text:
        matched_attraction_name = 'soaring'
        print(f"✅ 通过马达轴承关键字匹配到景点: soaring")
    elif 'rapids' in search_text or '激流' in search_text:
        matched_attraction_name = 'rapids'
        print(f"✅ 匹配到景点: rapids")
    elif 'mine' in search_text or 'train' in search_text or '矿山' in search_text:
        matched_attraction_name = 'mine train'
        print(f"✅ 匹配到景点: mine train")
    elif 'slinky' in search_text or '弹簧' in search_text:
        matched_attraction_name = 'slinky'
        print(f"✅ 匹配到景点: slinky")
    elif 'dumbo' in search_text or '小飞象' in search_text:
        matched_attraction_name = 'dumbo'
        print(f"✅ 匹配到景点: dumbo")
    elif 'carousel' in search_text or '旋转木马' in search_text:
        matched_attraction_name = 'carousel'
        print(f"✅ 匹配到景点: carousel")
    elif 'tron' in search_text:
        matched_attraction_name = 'tron'
        print(f"✅ 匹配到景点: tron")
    elif 'bo-' in search_text:
        # Tron设备使用BO-前缀，通过这个来识别Tron景点
        matched_attraction_name = 'tron'
        print(f"✅ 通过BO-前缀匹配到景点: tron")
    elif 'jetpack' in search_text or '喷气' in search_text:
        matched_attraction_name = 'jetpack'
        print(f"✅ 匹配到景点: jetpack")
    elif 'soaring' in search_text or '飞翔' in search_text:
        matched_attraction_name = 'soaring'
        print(f"✅ 匹配到景点: soaring")
    elif 'woody' in search_text or '胡迪' in search_text:
        matched_attraction_name = 'woody'
        print(f"✅ 匹配到景点: woody")
    elif 'hps' in search_text or '罐' in search_text:
        matched_attraction_name = 'hps'
        print(f"✅ 匹配到景点: hps")
    elif 'pirates' in search_text or '海盗' in search_text:
        matched_attraction_name = 'pirates'
        print(f"✅ 匹配到景点: pirates")
    elif '声光塔' in search_text:
        matched_attraction_name = '声光塔'
        print(f"✅ 匹配到景点: 声光塔")
    elif '护城河' in search_text:
        matched_attraction_name = '护城河'
        print(f"✅ 匹配到景点: 护城河")
    
    if not matched_attraction_name:
        print("❌ 未匹配到任何景点")
        equipment_info['match_details'] = {
            'method': 'hardcoded_match',
            'matched_attraction': None,
            'matched_equipment': None
        }
        return equipment_info
    
    # 从数据库获取对应的景点对象
    matched_attraction = Attraction.objects.filter(name__icontains=matched_attraction_name).first()
    if not matched_attraction:
        print(f"❌ 数据库中未找到景点: {matched_attraction_name}")
        return equipment_info
    
    print(f"\n=== 在景点 {matched_attraction.name} 下匹配设备 ===")
    
    # 硬编码设备匹配规则
    matched_equipment = None
    
    if matched_attraction_name == 'mine train':
        # Mine Train：匹配lift A、lift B 或 HPU
        if 'lift a' in search_text or 'lifta' in search_text or 'lift_a' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='lift a'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif 'lift b' in search_text or 'liftb' in search_text or 'lift_b' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='lift b'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif 'hpu' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='hpu'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
    
    elif matched_attraction_name == 'dumbo':
        # Dumbo：匹配1#、2#、3#、4#齿轮箱 或 轴承油脂
        for i in range(1, 5):
            if f'{i}#' in search_text or f'#{i}' in search_text or f'齿轮箱{i}' in search_text or f'（{i}#）' in search_text:
                matched_equipment = Equipment.objects.filter(
                    attraction=matched_attraction,
                    name__icontains=f'{i}#'
                ).first()
                if matched_equipment:
                    print(f"✅ 匹配到设备: {matched_equipment.name}")
                    break
        # Dumbo轴承油脂
        if not matched_equipment and '轴承油脂' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='轴承油脂'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
    elif matched_attraction_name == 'hps':
        # HPS：匹配大转盘、小转盘1、小转盘2、小转盘3、小转盘4
        if '大转盘' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='大转盘'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '小转盘1' in search_text or '小转盘 1' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='小转盘1'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '小转盘2' in search_text or '小转盘 2' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='小转盘2'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '小转盘3' in search_text or '小转盘 3' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='小转盘3'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '小转盘4' in search_text or '小转盘 4' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='小转盘4'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")


    elif matched_attraction_name == 'carousel':
        # Carousel：匹配3#或4#驱动齿轮箱，或轴承油脂设备
        if '锥齿' in search_text or ('轴承油脂' in search_text and ('1' in search_text or '#1' in search_text)):
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='锥齿'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '大转盘' in search_text and '轴承油脂' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='大转盘轴承油脂'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '3#' in search_text or '#3' in search_text or '驱动齿轮箱3' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='3#'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
        elif '4#' in search_text or '#4' in search_text or '驱动齿轮箱4' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='4#'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
    
    elif matched_attraction_name == 'jetpack':
        # Jetpack：匹配1#到8#齿轮箱 或 轴承油脂
        for i in range(1, 9):
            if f'{i}#' in search_text or f'#{i}' in search_text or f'jetpack{i}' in search_text or f'齿轮箱{i}' in search_text:
                matched_equipment = Equipment.objects.filter(
                    attraction=matched_attraction,
                    name__icontains=f'{i}#'
                ).first()
                if matched_equipment:
                    print(f"✅ 匹配到设备: {matched_equipment.name}")
                    break
        # Jetpack轴承油脂
        if not matched_equipment and '轴承油脂' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='轴承油脂'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
    
    elif matched_attraction_name == 'slinky':
        print("🔍 开始Slinky设备特殊匹配逻辑")
        # Slinky：匹配1#到12# Kicker Wheel - 使用精确的正则表达式匹配
        # 按照从大到小的顺序匹配，避免10#匹配到1#
        for i in range(12, 0, -1):
            # 使用正则表达式进行精确匹配，确保是完整的数字而不是部分匹配
            pattern1 = rf'\b{i}#\b'  # 匹配 "1#" 但不匹配 "10#" 中的 "1#"
            pattern2 = rf'#{i}\b'   # 匹配 "#1" 但不匹配 "#10" 中的 "#1"
            pattern3 = rf'\b{i}号\b' # 匹配 "1号" 但不匹配 "10号" 中的 "1号"
            
            print(f"  🔍 测试模式 {i}: {pattern1}, {pattern2}, {pattern3}")
            
            match1 = re.search(pattern1, search_text, re.IGNORECASE)
            match2 = re.search(pattern2, search_text, re.IGNORECASE)
            match3 = re.search(pattern3, search_text, re.IGNORECASE)
            
            if match1 or match2 or match3:
                print(f"  ✅ 找到匹配 {i}: match1={bool(match1)}, match2={bool(match2)}, match3={bool(match3)}")
                matched_equipment = Equipment.objects.filter(
                    attraction=matched_attraction,
                    name__icontains=f'#{i}'
                ).first()
                if matched_equipment:
                    print(f"✅ 匹配到设备: {matched_equipment.name}")
                    break
            else:
                print(f"  ❌ 未找到匹配 {i}")
        
        # 如果正则匹配失败，尝试直接字符串匹配（从大到小）
        if not matched_equipment:
            print("🔍 正则匹配失败，尝试字符串匹配")
            for i in range(12, 0, -1):
                if f'#{i}' in search_text:
                    print(f"  ✅ 字符串匹配找到 #{i}")
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        name__icontains=f'#{i}'
                    ).first()
                    if matched_equipment:
                        print(f"✅ 字符串匹配到设备: {matched_equipment.name}")
                        break
                    else:
                        print(f"  ❌ 数据库中未找到设备 #{i}")
                else:
                    print(f"  ❌ 字符串匹配未找到 #{i}")
        
        if not matched_equipment:
            print("❌ Slinky特殊匹配逻辑失败")
    
    elif matched_attraction_name == 'woody':
        # Woody：匹配1#到8#齿轮箱 - 处理多种格式
        for i in range(1, 9):
            # 检查多种可能的格式
            if (f'{i}#' in search_text or 
                f'#{i}' in search_text or 
                f'gearbox{i}' in search_text or
                f'gearbox {i}' in search_text or
                f'齿轮箱{i}' in search_text):
                matched_equipment = Equipment.objects.filter(
                    attraction=matched_attraction,
                    name__icontains=f'{i}#'
                ).first()
                if matched_equipment:
                    print(f"✅ 匹配到设备: {matched_equipment.name}")
                    break
    
    elif matched_attraction_name == 'tron':
        print("🔍 开始Tron设备特殊匹配逻辑")
        # Tron：完整枚举所有29个设备的匹配逻辑
        # 按照文件名中的模式进行精确匹配
        tron_patterns = [
            # BO-Z6系列
            ('BO-Z6-03', ['左', '右']),
            ('BO-Z6-02', ['左', '右']),
            ('BO-Z6-01', ['左', '右']),
            # BO-UB系列
            ('BO-UB-08', ['左', '右']),
            ('BO-UB-07', ['左', '右']),
            # BO-UA系列
            ('BO-UA-08', ['左', '右']),
            ('BO-UA-07', ['左', '右']),
            # BO-PL系列
            ('BO-PL-09', ['左', '右']),
            ('BO-PL-08', ['左', '右']),
            ('BO-PL-07', ['左', '右']),
            # BO-H2系列
            ('BO-H2-02', ['左', '右']),
            ('BO-H2-01', ['左', '右']),
            # BO-H1系列
            ('BO-H1-02', ['左', '右']),
            ('BO-H1-01', ['左', '右'])
        ]
        
        for pattern, positions in tron_patterns:
            for position in positions:
                # 构造数据库中的设备名称（无空格）
                db_equipment_name = f"{pattern}{position}"
                # 构造文件名中的模式（有空格）
                filename_pattern = f"{pattern} {position}"
                
                print(f"  🔍 测试模式: {db_equipment_name} vs {filename_pattern}")
                
                # 检查文件名中是否包含模式
                if filename_pattern.lower() in search_text:
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        name=db_equipment_name
                    ).first()
                    if matched_equipment:
                        print(f"✅ 匹配到设备: {matched_equipment.name}")
                        break
                # 也检查无空格的版本
                elif pattern.lower() in search_text and position in search_text:
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        name=db_equipment_name
                    ).first()
                    if matched_equipment:
                        print(f"✅ 分离匹配到设备: {matched_equipment.name}")
                        break
            
            if matched_equipment:
                break
        
        # 如果特殊匹配失败，尝试通用匹配
        if not matched_equipment:
            print("🔍 特殊匹配失败，尝试通用匹配")
            equipment_list = Equipment.objects.filter(attraction=matched_attraction)
            for equipment in equipment_list:
                # 移除空格进行比较
                equipment_name_no_space = equipment.name.replace(' ', '').lower()
                search_text_no_space = search_text.replace(' ', '')
                if equipment_name_no_space in search_text_no_space:
                    matched_equipment = equipment
                    print(f"✅ 通用匹配到设备: {equipment.name}")
                    break
    
    elif matched_attraction_name == 'soaring':
        print("🔍 开始Soaring设备特殊匹配逻辑")
        
        # Soaring马达轴承设备匹配模式
        # 格式: 马达轴承 - AA前端, 马达轴承 - AA后端 等
        motor_bearing_patterns = [
            ('AA', '前端'), ('AA', '后端'),
            ('AB', '前端'), ('AB', '后端'),
            ('AC', '前端'), ('AC', '后端'),
            ('BA', '前端'), ('BA', '后端'),
            ('BB', '前端'), ('BB', '后端'),
            ('BC', '前端'), ('BC', '后端'),
        ]
        
        # 首先尝试匹配马达轴承设备
        for code, position in motor_bearing_patterns:
            # 构造可能的匹配模式
            patterns_to_check = [
                f'马达轴承{code}{position}',
                f'马达轴承{code} {position}',
                f'马达轴承-{code}-{position}',
                f'马达轴承_{code}_{position}',
                f'{code}{position}',
                f'{code} {position}',
                f'{code}-{position}',
                f'{code}_{position}',
            ]
            
            for pattern in patterns_to_check:
                if pattern.lower() in search_text:
                    print(f"  ✅ 找到马达轴承模式: {pattern}")
                    # 在数据库中查找匹配的设备
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        name__icontains='马达轴承',
                        name__icontains=code,
                        name__icontains=position
                    ).first()
                    if matched_equipment:
                        print(f"✅ 匹配到马达轴承设备: {matched_equipment.name}")
                        break
                    else:
                        # 尝试更宽松的匹配
                        matched_equipment = Equipment.objects.filter(
                            attraction=matched_attraction,
                            name__icontains=code,
                            name__icontains=position
                        ).first()
                        if matched_equipment:
                            print(f"✅ 宽松匹配到设备: {matched_equipment.name}")
                            break
            
            if matched_equipment:
                break
        
        # 如果马达轴承匹配失败，尝试原有的AA、AB、AC等设备匹配
        if not matched_equipment:
            print("🔍 马达轴承匹配失败，尝试原有设备匹配")
            soaring_patterns = ['AA', 'AB', 'AC', 'BA', 'BB', 'BC']
            for pattern in soaring_patterns:
                # 检查文件名中是否包含模式（处理多种格式）
                pattern_found = False
                
                # 检查各种可能的模式组合
                if (pattern in search_text or 
                    f'soaring{pattern.lower()}' in search_text or
                    f'soaring_{pattern.lower()}' in search_text or
                    f'soaring-{pattern.lower()}' in search_text or
                    f'soaring {pattern.lower()}' in search_text):
                    pattern_found = True
                    print(f"  🔍 找到模式 {pattern} 在搜索文本中")
                
                if pattern_found:
                    # 首先尝试匹配设备名称中包含模式的设备（如"AA设备"）
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        name__icontains=pattern
                    ).first()
                    if matched_equipment:
                        print(f"✅ 通过设备名称匹配到设备: {matched_equipment.name}")
                        break
                    
                    # 如果设备名称匹配失败，尝试匹配位置信息
                    matched_equipment = Equipment.objects.filter(
                        attraction=matched_attraction,
                        location__icontains=pattern
                    ).first()
                    if matched_equipment:
                        print(f"✅ 通过位置匹配到设备: {matched_equipment.name}")
                        break
                    
                    # 尝试更宽松的匹配，移除下划线和连字符
                    clean_search_text = search_text.replace('_', '').replace('-', '').replace(' ', '')
                    if pattern.lower() in clean_search_text:
                        matched_equipment = Equipment.objects.filter(
                            attraction=matched_attraction,
                            name__icontains=pattern
                        ).first()
                        if matched_equipment:
                            print(f"✅ 通过清理后的文本匹配到设备: {matched_equipment.name}")
                            break
    
    elif matched_attraction_name == 'rapids':
        # Rapids：匹配齿轮箱
        if '齿轮箱' in search_text or 'gearbox' in search_text:
            matched_equipment = Equipment.objects.filter(
                attraction=matched_attraction,
                name__icontains='齿轮箱'
            ).first()
            if matched_equipment:
                print(f"✅ 匹配到设备: {matched_equipment.name}")
    
    # 如果特殊匹配没找到，尝试通用匹配
    if not matched_equipment:
        equipment_list = Equipment.objects.filter(attraction=matched_attraction)
        for equipment in equipment_list:
            if equipment.name.lower() in search_text:
                matched_equipment = equipment
                print(f"✅ 通用匹配到设备: {equipment.name}")
                break
    
    # 更新设备信息
    if matched_equipment:
        equipment_info['matched_equipment_id'] = matched_equipment.id
        equipment_info['matched_attraction_id'] = matched_equipment.attraction.id
        equipment_info['matched_equipment_name'] = matched_equipment.name
        equipment_info['matched_location'] = matched_equipment.location
        equipment_info['matched_attraction_name'] = matched_equipment.attraction.name
        equipment_info['match_details'] = {
            'method': 'hardcoded_match',
            'matched_attraction': matched_attraction.name,
            'matched_equipment': matched_equipment.name
        }
        print(f"\n✅ 最终匹配结果: 景点={matched_attraction.name}, 设备={matched_equipment.name}")
    else:
        print(f"\n❌ 在景点 {matched_attraction.name} 下未找到匹配的设备")
        equipment_info['match_details'] = {
            'method': 'hardcoded_match',
            'matched_attraction': matched_attraction.name,
            'matched_equipment': None
        }
    
    return equipment_info

def enhance_equipment_info_with_context(equipment_info: Dict[str, any], md_content: str = "") -> Dict[str, any]:
    """使用上下文信息增强设备信息"""
    # 简单的上下文增强，可以后续扩展
    return equipment_info

def find_or_create_equipment(equipment_info: Dict[str, any]) -> Tuple[Any, bool]:
    """
    根据设备信息查找或创建设备
    优先匹配现有的标准设备名称，而不是创建新设备

    Args:
        equipment_info: 设备信息字典

    Returns:
        (equipment, created) 元组，equipment是设备对象，created表示是否新创建
    """
    from oil_records.models import Attraction, Equipment

    equipment_name = equipment_info.get('equipment_name', '').strip()
    location = equipment_info.get('location', '').strip()
    equipment_type = equipment_info.get('equipment_type', '').strip()
    filename = equipment_info.get('filename', '')

    if not equipment_name:
        raise ValueError("设备名称不能为空")

    print(f"🔍 查找设备: {equipment_name}, 位置: {location}, 文件名: {filename}")

    # 1. 首先检查设备信息中是否已经包含匹配的设备
    if 'matched_equipment' in equipment_info and equipment_info['matched_equipment']:
        equipment = equipment_info['matched_equipment']
        print(f"✅ 使用预匹配的设备: {equipment.name}")
        return equipment, False

    # 2. 尝试精确匹配现有设备
    equipment = Equipment.objects.filter(
        name__iexact=equipment_name,
        location__iexact=location
    ).first()

    if equipment:
        print(f"✅ 精确匹配到现有设备: {equipment.name}")
        return equipment, False

    # 3. 尝试只匹配设备名称
    equipment = Equipment.objects.filter(
        name__iexact=equipment_name
    ).first()

    if equipment:
        print(f"✅ 匹配到现有设备: {equipment.name}")
        return equipment, False

    # 4. 如果没有找到，使用智能匹配逻辑（基于文件名和设备名称）
    print(f"🔄 未找到精确匹配，开始智能匹配...")

    # 使用simple_match_equipment进行匹配
    matched_info = simple_match_equipment(equipment_info, filename)

    # 检查是否通过ID匹配到了设备
    if 'matched_equipment_id' in matched_info and matched_info['matched_equipment_id']:
        try:
            equipment = Equipment.objects.get(id=matched_info['matched_equipment_id'])
            print(f"✅ 智能匹配到现有设备: {equipment.name}")
            return equipment, False
        except Equipment.DoesNotExist:
            print(f"⚠️ 匹配到的设备ID {matched_info['matched_equipment_id']} 不存在")

    # 检查是否有直接匹配的设备对象
    if 'matched_equipment' in matched_info and matched_info['matched_equipment']:
        equipment = matched_info['matched_equipment']
        print(f"✅ 智能匹配到现有设备: {equipment.name}")
        return equipment, False

    # 5. 如果仍然没有找到，尝试智能匹配到现有景点（最后兜底）
    attraction = None
    equipment_name_lower = equipment_name.lower()
    filename_lower = filename.lower()
    search_text = f"{equipment_name_lower} {filename_lower}"

    # 硬编码匹配景点
    if 'rapids' in search_text or '激流' in search_text:
        attraction = Attraction.objects.filter(name__icontains='rapids').first()
    elif 'mine' in search_text or 'train' in search_text or '矿山' in search_text:
        attraction = Attraction.objects.filter(name__icontains='mine train').first()
    elif 'slinky' in search_text or '弹簧' in search_text:
        attraction = Attraction.objects.filter(name__icontains='slinky').first()
    elif 'dumbo' in search_text or '小飞象' in search_text:
        attraction = Attraction.objects.filter(name__icontains='dumbo').first()
    elif 'carousel' in search_text or '旋转木马' in search_text:
        attraction = Attraction.objects.filter(name__icontains='carousel').first()
    elif 'tron' in equipment_name_lower:
        attraction = Attraction.objects.filter(name__icontains='tron').first()
    elif 'jetpack' in equipment_name_lower or '喷气' in equipment_name_lower:
        attraction = Attraction.objects.filter(name__icontains='jetpack').first()
    elif 'soaring' in equipment_name_lower or '飞翔' in equipment_name_lower:
        attraction = Attraction.objects.filter(name__icontains='soaring').first()
    elif 'woody' in equipment_name_lower or '胡迪' in equipment_name_lower:
        attraction = Attraction.objects.filter(name__icontains='woody').first()
    elif 'hps' in equipment_name_lower or '罐' in equipment_name_lower:
        attraction = Attraction.objects.filter(name__icontains='hps').first()
    
    # 如果没有找到匹配的设备，抛出错误而不是创建新设备
    # 这样可以强制使用现有的标准设备名称
    error_msg = f"无法匹配到现有设备: 设备名称='{equipment_name}', 位置='{location}', 文件名='{filename}'"
    print(f"❌ {error_msg}")
    print("💡 建议：请检查设备名称是否与下拉菜单中的标准名称匹配")

    raise ValueError(error_msg)

# 保持向后兼容
def smart_match_equipment_with_database(equipment_info: Dict[str, any], filename: str = "") -> Dict[str, any]:
    """向后兼容的函数名"""
    return simple_match_equipment(equipment_info, filename)

def extract_equipment_number(search_text: str) -> str:
    """提取设备编号"""
    # 查找编号模式：1#、2#、#1、#2等
    number_patterns = [
        r'(\d+)#',
        r'#(\d+)',
        r'齿轮箱(\d+)',
        r'设备(\d+)',
        r'(\d+)号'
    ]
    
    for pattern in number_patterns:
        match = re.search(pattern, search_text)
        if match:
            return match.group(1)
    
    return ""

def extract_location_info(search_text: str) -> str:
    """提取位置信息"""
    # 直接硬编码匹配位置
    if 'left' in search_text.lower() or '左' in search_text:
        return '左'
    elif 'right' in search_text.lower() or '右' in search_text:
        return '右'
    elif 'front' in search_text.lower() or '前' in search_text:
        return '前'
    elif 'rear' in search_text.lower() or '后' in search_text:
        return '后'
    
    return ""

# 主函数：完整的设备信息提取流程
def extract_equipment_info_complete(md_content: str, filename: str = "") -> Dict[str, any]:
    """
    完整的设备信息提取流程
    
    Args:
        md_content: OCR处理后的MD内容
        filename: PDF文件名
        
    Returns:
        完整的设备信息字典
    """
    # 1. 基础提取
    equipment_info = extract_equipment_info(md_content, filename)
    
    # 2. 数据库硬编码匹配
    equipment_info = simple_match_equipment(equipment_info, filename)
    
    # 3. 上下文增强
    equipment_info = enhance_equipment_info_with_context(equipment_info, md_content)
    
    return equipment_info

if __name__ == "__main__":
    # 测试代码
    test_md = """
    # 油品检测报告
    
    设备名称：Dumbo齿轮箱1#
    位置：左
    设备类型：齿轮箱
    
    检测日期：2024-01-15
    """
    
    test_filename = "32868260_Dumbo齿轮箱1_A5LLkEj.pdf"
    
    result = extract_equipment_info_complete(test_md, test_filename)
    print(json.dumps(result, ensure_ascii=False, indent=2))
