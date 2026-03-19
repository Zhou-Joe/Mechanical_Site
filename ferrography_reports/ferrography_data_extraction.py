#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
铁谱报告数据提取模块
从OCR生成的MD内容中提取铁谱分析指标
"""

import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


def extract_ferrography_data_from_md(md_content: str) -> Dict[str, Any]:
    """
    从MD内容中提取完整的铁谱分析数据
    
    Returns:
        {
            'report_number': '报告编号',
            'sample_date': '采样日期',
            'report_date': '报告日期',
            'particles': [
                {
                    'particle_type': '颗粒类型',
                    'concentration': '浓度',
                    'size_range': '尺寸范围',
                    'morphology': '形貌描述',
                    'wear_mechanism': '磨损机理',
                    'severity_level': '严重等级'
                }
            ],
            'diagnosis': {
                'overall_assessment': '总体评价',
                'wear_status': '磨损状态',
                'recommendations': '建议措施'
            }
        }
    """
    if not md_content:
        return {}
    
    result = {
        'report_number': '',
        'sample_date': None,
        'report_date': None,
        'particles': [],
        'diagnosis': {}
    }
    
    # 清理MD内容
    cleaned_content = clean_md_content(md_content)
    
    # 提取报告信息（传递原始内容用于表格日期提取）
    result['report_number'] = extract_report_number(cleaned_content)
    result['sample_date'] = extract_sample_date(md_content)  # 使用原始内容
    result['report_date'] = extract_report_date(cleaned_content)
    
    # 提取颗粒信息（优先从表格提取）
    from .table_parser import parse_all_tables, find_particle_table, extract_particles_from_table_data
    
    tables = parse_all_tables(md_content)
    print(f"📊 找到 {len(tables)} 个表格")
    
    particle_table = find_particle_table(tables)
    if particle_table:
        print("✅ 找到颗粒信息表格")
        result['particles'] = extract_particles_from_table_data(particle_table)
    else:
        # 尝试从所有表格提取
        all_particles = []
        for table in tables:
            particles = extract_particles_from_table_data(table)
            if particles:
                all_particles.extend(particles)
        
        if all_particles:
            result['particles'] = all_particles
        else:
            # 从文本提取作为备选
            result['particles'] = extract_particles_from_text(cleaned_content)
    
    print(f"✅ 共提取到 {len(result['particles'])} 个颗粒")
    
    # 提取诊断信息（使用原始MD内容，保留HTML表格）
    result['diagnosis'] = extract_diagnosis(md_content)
    
    return result


def clean_md_content(md_content: str) -> str:
    """清理MD内容，移除HTML标签但保留文本"""
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', ' ', md_content)
    # 规范化空白字符
    text = re.sub(r'\s+', ' ', text)
    # 移除特殊字符
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
    return text.strip()


def extract_report_number(content: str) -> str:
    """提取报告编号"""
    patterns = [
        r'报告编号[：:]\s*([A-Za-z0-9\-]+)',
        r'编号[：:]\s*([A-Za-z0-9\-]+)',
        r'No\.?\s*[:：]?\s*([A-Za-z0-9\-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ''


def extract_sample_date(content: str) -> Optional[str]:
    """提取采样日期"""
    # 先尝试从表格中提取日期（优先）
    date_from_table = extract_date_from_table(content)
    if date_from_table:
        return date_from_table
    
    # 再尝试从文本中提取
    patterns = [
        r'采样日期[：:]\s*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2})',
        r'样品日期[：:]\s*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2})',
        r'取样日期[：:]\s*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            date_str = normalize_date(match.group(1))
            if date_str:
                return date_str
    
    return None


def extract_date_from_table(content: str) -> Optional[str]:
    """从表格中提取日期（诊断建议/总体评价旁边的日期）"""
    # 查找表格中的日期，格式如：<td>诊断建议</td><td>2026/1/15</td>
    # 或 <td></td><td>诊断建议</td><td>2026/1/15</td><td></td>
    
    # 模式1: 诊断建议 + 日期在同一行
    table_date_patterns = [
        # <td>诊断建议</td><td>2026/1/15</td>
        r'>诊断建议</td[^>]*>\s*<td[^>]*>(\d{4}/\d{1,2}/\d{1,2})</td>',
        # <td>总体评价</td><td>2026/1/15</td>
        r'>总体评价</td[^>]*>\s*<td[^>]*>(\d{4}/\d{1,2}/\d{1,2})</td>',
        # 任何表格单元格中的日期
        r'<td[^>]*>(\d{4}/\d{1,2}/\d{1,2})</td>',
    ]
    
    for pattern in table_date_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            # 取第一个匹配的日期
            date_str = normalize_date(matches[0])
            if date_str:
                print(f"✅ 从表格提取到日期: {date_str}")
                return date_str
    
    # 使用表格解析器查找日期
    from .table_parser import parse_all_tables
    
    tables = parse_all_tables(content)
    for table in tables:
        for row in table.get('rows', []):
            cells = row.get('cells', [])
            for i, cell in enumerate(cells):
                cell_content = cell.get('content', '').strip()
                
                # 检查是否是关键词单元格
                if cell_content in ['诊断建议', '总体评价', '报告日期', '采样日期', '分析日期']:
                    # 查找相邻单元格中的日期
                    for j in range(i + 1, min(i + 3, len(cells))):
                        next_content = cells[j].get('content', '').strip()
                        date_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', next_content)
                        if date_match:
                            date_str = normalize_date(date_match.group(1))
                            if date_str:
                                print(f"✅ 从表格[{cell_content}]旁提取到日期: {date_str}")
                                return date_str
                
                # 直接检查单元格是否包含日期格式
                date_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2})', cell_content)
                if date_match:
                    date_str = normalize_date(date_match.group(1))
                    if date_str:
                        print(f"✅ 从表格单元格提取到日期: {date_str}")
                        return date_str
    
    return None


def extract_report_date(content: str) -> Optional[str]:
    """提取报告日期"""
    patterns = [
        r'报告日期[：:]\s*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2})',
        r'分析日期[：:]\s*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            date_str = normalize_date(match.group(1))
            if date_str:
                return date_str
    return None


def normalize_date(date_str: str) -> Optional[str]:
    """标准化日期格式为 YYYY-MM-DD"""
    try:
        # 清理日期字符串
        date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
        date_str = date_str.replace('/', '-').replace('.', '-')
        
        # 尝试解析
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%Y-%m-%d')
    except:
        return None


def extract_particles_from_text(content: str) -> List[Dict[str, Any]]:
    """从文本中提取颗粒信息（备选方案）"""
    particles = []
    
    # 常见颗粒类型及其特征描述
    particle_types = {
        '球形颗粒': ['球形', '球状', 'sphere'],
        '切削颗粒': ['切削', '切屑', 'cutting'],
        '疲劳颗粒': ['疲劳', 'fatigue'],
        '层状颗粒': ['层状', '层片', 'lamellar'],
        '严重滑动颗粒': ['严重滑动', '滑动', 'severe sliding'],
        '红色氧化物': ['红色氧化物', '红氧化物', 'red oxide'],
        '黑色氧化物': ['黑色氧化物', '黑氧化物', 'black oxide'],
        '有色金属颗粒': ['有色金属', '铜', '铝', 'non-ferrous'],
    }
    
    # 按颗粒类型查找
    for particle_type, keywords in particle_types.items():
        for keyword in keywords:
            # 查找包含该关键词的行
            pattern = rf'{keyword}[^\n]*'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            for match in matches:
                particle = parse_particle_line(match, particle_type)
                if particle:
                    particles.append(particle)
    
    return particles


def parse_particle_line(line: str, default_type: str = '') -> Optional[Dict[str, Any]]:
    """解析颗粒信息行"""
    particle = {
        'particle_type': default_type,
        'concentration': '',
        'size_range': '',
        'morphology': '',
        'wear_mechanism': '',
        'severity_level': ''
    }
    
    # 提取浓度 (如: 15/ml, 20个/ml)
    concentration_match = re.search(r'(\d+)\s*(?:个)?\s*/\s*ml', line, re.IGNORECASE)
    if concentration_match:
        particle['concentration'] = concentration_match.group(0)
    
    # 提取尺寸范围 (如: 5-10μm, <5μm)
    size_match = re.search(r'([<>]?\d+[\-\d]*\s*μm|微米)', line)
    if size_match:
        particle['size_range'] = size_match.group(1)
    
    # 提取严重等级
    severity_keywords = ['正常', '轻微', '中等', '严重', '危急']
    for keyword in severity_keywords:
        if keyword in line:
            particle['severity_level'] = keyword
            break
    
    # 整行作为形貌描述（去除已提取的信息）
    description = line
    description = re.sub(r'\d+\s*(?:个)?\s*/\s*ml', '', description)
    description = re.sub(r'[<>]?\d+[\-\d]*\s*μm', '', description)
    particle['morphology'] = description.strip('：: ')
    
    return particle


def extract_diagnosis(content: str) -> Dict[str, str]:
    """提取诊断结论"""
    diagnosis = {
        'overall_assessment': '',
        'wear_status': '',
        'recommendations': ''
    }
    
    # 先清理HTML标签，保留文本
    text_content = clean_md_content(content)
    
    print(f"🔍 开始提取诊断结论...")
    
    # 方法1：从文本内容中查找诊断建议后面的结论
    # 格式通常是：诊断建议 2026/1/15 磨损正常，请正常监控。
    
    # 在清理后的文本中查找
    idx = text_content.find('诊断建议')
    if idx != -1:
        # 取诊断建议后面的300字符
        after_diagnosis = text_content[idx:idx+300]
        print(f"  📝 诊断建议后的内容: {after_diagnosis[:100]}...")
        
        # 移除"诊断建议"关键词和日期
        after_diagnosis = after_diagnosis.replace('诊断建议', '')
        after_diagnosis = re.sub(r'\d{4}/\d{1,2}/\d{1,2}', '', after_diagnosis)
        after_diagnosis = after_diagnosis.strip()
        
        # 提取第一句有意义的中文句子
        sentences = re.split(r'[。！？\n]', after_diagnosis)
        for sentence in sentences:
            sentence = sentence.strip()
            # 跳过太短的句子
            if len(sentence) > 5:
                # 检查是否包含磨损/监控相关内容
                if '磨损' in sentence or '正常' in sentence or '监控' in sentence or '建议' in sentence:
                    # 清理多余空格
                    sentence = re.sub(r'\s+', '', sentence)
                    diagnosis['overall_assessment'] = sentence
                    print(f"✅ 提取诊断结论: {sentence}")
                    break
    
    # 方法2：查找表格后的结论文本
    if not diagnosis['overall_assessment']:
        # 查找包含诊断建议的表格后面的文本
        # 表格格式：<table>...诊断建议...</table>磨损正常，请正常监控。
        pattern = r'</table>\s*\n*\s*([^<\n]+?磨损[^\n<]*)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            conclusion = match.group(1).strip()
            conclusion = re.sub(r'\s+', '', conclusion)
            if conclusion and len(conclusion) > 5:
                diagnosis['overall_assessment'] = conclusion
                print(f"✅ 从表格后提取诊断结论: {conclusion}")
    
    # 提取总体评价
    # 首先尝试提取"总体评价"后面的简短结论
    overall_patterns = [
        # 总体评价/诊断结论 + 日期 + 简短结论（到#或换行）
        r'总体评价[：:\s]*\n*\d{4}/\d{1,2}/\d{1,2}\s*([^#\n]{5,100})',
        r'诊断结论[：:\s]*\n*\d{4}/\d{1,2}/\d{1,2}\s*([^#\n]{5,100})',
        r'分析结论[：:\s]*\n*\d{4}/\d{1,2}/\d{1,2}\s*([^#\n]{5,100})',
        # 诊断建议/结论 + 换行 + 内容（到下一个标题或结束）
        r'总体评价[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:磨损状态|建议措施|处理意见|#|$))',
        r'诊断建议[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:诊断结论|分析结论|磨损状态|建议措施|处理意见|#|$))',
        r'诊断结论[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:分析结论|磨损状态|建议措施|处理意见|#|$))',
        r'分析结论[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:磨损状态|建议措施|处理意见|#|$))',
    ]
    
    for pattern in overall_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            text = clean_text(match.group(1))
            # 提取核心结论（去除图片引用等多余内容）
            text = extract_core_conclusion(text)
            if len(text) > 5:  # 确保提取到有效内容
                diagnosis['overall_assessment'] = text
                print(f"✅ 提取诊断结论: {text}")
                break
    
    # 如果上面的模式没匹配到，尝试更宽松的模式
    if not diagnosis['overall_assessment']:
        # 查找"诊断建议"或"诊断结论"后面的所有文本（直到遇到空行或新标题）
        loose_pattern = r'(?:诊断建议|诊断结论|分析结论|诊断意见)[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:[一二三四五六七八九十]、|\d+\.|#|$))'
        match = re.search(loose_pattern, text_content, re.IGNORECASE)
        if match:
            text = clean_text(match.group(1))
            text = extract_core_conclusion(text)
            if len(text) > 5:
                diagnosis['overall_assessment'] = text
                print(f"✅ 提取诊断结论(宽松模式): {text}")
    
    # 提取磨损状态
    wear_status_keywords = {
        '正常磨损': ['正常磨损', 'normal wear'],
        '轻微磨损': ['轻微磨损', 'mild wear'],
        '中等磨损': ['中等磨损', 'moderate wear'],
        '严重磨损': ['严重磨损', 'severe wear'],
        '异常磨损': ['异常磨损', 'abnormal wear'],
    }
    
    for status, keywords in wear_status_keywords.items():
        for keyword in keywords:
            if keyword in content.lower():
                diagnosis['wear_status'] = status
                break
        if diagnosis['wear_status']:
            break
    
    # 提取建议措施
    recommendation_patterns = [
        # 建议措施 + 日期 + 简短内容
        r'建议措施[：:\s]*\n*\d{4}/\d{1,2}/\d{1,2}\s*([^#\n]{5,100})',
        # 建议措施 + 换行 + 内容（到下一个标题或结束）
        r'建议措施[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:[一二三四五六七八九十]、|\d+\.|#|$))',
        r'处理意见[：:\s]*\n*([\s\S]*?)(?=\n\s*(?:[一二三四五六七八九十]、|\d+\.|#|$))',
        r'建议[：:\s]*\n*([\s\S]{10,500}?)(?=\n\s*\n|\Z)',
    ]
    
    for pattern in recommendation_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            text = clean_text(match.group(1))
            text = extract_core_conclusion(text)
            if len(text) > 5:
                diagnosis['recommendations'] = text
                print(f"✅ 提取建议措施: {text}")
                break
    
    if not diagnosis['recommendations']:
        print(f"⚠️ 未能提取建议措施")
    
    return diagnosis


def extract_core_conclusion(text: str) -> str:
    """提取核心诊断结论，去除多余内容"""
    # 移除图片引用 ![](...)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 移除单独的链接/路径
    text = re.sub(r'images/[^\s]*', '', text)
    # 移除表格相关内容
    text = re.sub(r'磨损颗粒类型.*', '', text)
    text = re.sub(r'正常磨损磨粒.*', '', text)
    text = re.sub(r'切削磨损颗粒.*', '', text)
    text = re.sub(r'注：.*', '', text)
    text = re.sub(r'授权签字人.*', '', text)
    # 移除放大倍数等描述
    text = re.sub(r'放大倍数.*', '', text)
    # 提取第一行核心内容（通常是结论）
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        # 返回第一行非空的简短结论
        first_line = lines[0]
        # 如果第一行太长，截取前100字符
        if len(first_line) > 100:
            first_line = first_line[:100] + '...'
        return first_line
    return text.strip()


def clean_text(text: str) -> str:
    """清理文本内容"""
    # 规范化空白
    text = re.sub(r'\s+', ' ', text)
    # 移除多余空行
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()
