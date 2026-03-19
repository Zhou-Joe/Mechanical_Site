#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HTML表格解析器
专门用于解析MinerU OCR输出的HTML表格
"""

import re
from typing import List, Dict, Any, Optional
from html.parser import HTMLParser


class TableParser(HTMLParser):
    """HTML表格解析器"""
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_data = []
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = {'rows': []}
        elif tag == 'tr':
            self.in_row = True
            self.current_row = {'cells': []}
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.cell_data = []
            # 处理rowspan和colspan
            attrs_dict = dict(attrs)
            self.current_cell = {
                'rowspan': int(attrs_dict.get('rowspan', 1)),
                'colspan': int(attrs_dict.get('colspan', 1)),
                'is_header': tag == 'th'
            }
    
    def handle_endtag(self, tag):
        if tag == 'table':
            if self.current_table:
                self.tables.append(self.current_table)
            self.in_table = False
            self.current_table = None
        elif tag == 'tr':
            if self.current_row and self.current_table:
                self.current_table['rows'].append(self.current_row)
            self.in_row = False
            self.current_row = None
        elif tag in ('td', 'th'):
            if self.current_cell and self.current_row:
                self.current_cell['content'] = ''.join(self.cell_data).strip()
                self.current_row['cells'].append(self.current_cell)
            self.in_cell = False
            self.current_cell = None
    
    def handle_data(self, data):
        if self.in_cell:
            self.cell_data.append(data)
    
    def parse(self, html: str) -> List[Dict]:
        """解析HTML中的表格"""
        self.tables = []
        self.feed(html)
        return self.tables


def parse_all_tables(md_content: str) -> List[Dict]:
    """
    从MD内容中解析所有表格
    
    Returns:
        表格列表，每个表格包含rows，每行包含cells
    """
    # 查找所有表格
    table_pattern = r'<table[^>]*>.*?</table>'
    table_htmls = re.findall(table_pattern, md_content, re.DOTALL | re.IGNORECASE)
    
    all_tables = []
    for table_html in table_htmls:
        parser = TableParser()
        tables = parser.parse(table_html)
        all_tables.extend(tables)
    
    return all_tables


def find_particle_table(tables: List[Dict]) -> Optional[Dict]:
    """
    查找颗粒信息表格
    
    通过检查表头来识别颗粒表格
    """
    particle_keywords = ['颗粒', '类型', '浓度', '尺寸', '形貌', '磨损']
    
    for table in tables:
        if not table['rows']:
            continue
        
        # 检查第一行（表头）
        first_row = table['rows'][0]
        header_text = ' '.join([cell.get('content', '') for cell in first_row['cells']])
        
        # 如果包含颗粒相关关键词，认为是颗粒表格
        if any(keyword in header_text for keyword in particle_keywords):
            return table
    
    return None


def extract_particles_from_table_data(table: Dict) -> List[Dict[str, Any]]:
    """
    从表格数据中提取颗粒信息
    
    Args:
        table: 解析后的表格数据
        
    Returns:
        颗粒信息列表
    """
    if not table or not table.get('rows'):
        return []
    
    rows = table['rows']
    if len(rows) < 2:  # 需要至少表头和一行数据
        return []
    
    # 解析表头
    header_row = rows[0]
    headers = []
    for cell in header_row['cells']:
        content = clean_text(cell.get('content', ''))
        headers.append(content)
    
    print(f"📋 表头: {headers}")
    
    # 严重等级选项（用于检测打勾的列）
    severity_levels = ['无', '少量', '中等', '大量']
    severity_columns = {}  # 列索引 -> 等级值
    
    # 尺寸列索引
    size_column = None
    
    # 构建列索引映射
    for i, header in enumerate(headers):
        # 检查是否是等级选项列
        for level in severity_levels:
            if level == header.strip():  # 精确匹配
                severity_columns[i] = level
                print(f"  📍 发现等级列 [{i}]: {level}")
                break
        
        # 检查是否是尺寸列
        if '尺寸' in header or 'um' in header.lower() or 'μm' in header:
            size_column = i
            print(f"  📍 发现尺寸列 [{i}]: {header}")
    
    print(f"📊 等级列映射: {severity_columns}")
    print(f"📊 尺寸列: {size_column}")
    
    # 提取数据行
    particles = []
    for row in rows[1:]:  # 跳过表头
        cells = row['cells']
        if not cells:
            continue
        
        # 第一列是颗粒类型
        particle_type = clean_text(cells[0].get('content', '')) if cells else ''
        
        if not particle_type:
            continue
        
        # 创建颗粒数据
        particle = {
            'particle_type': particle_type,
            'concentration': '',
            'size_range': '',
            'morphology': '',
            'wear_mechanism': '',
            'severity_level': '无'  # 默认无
        }
        
        # 检测严重等级（通过检查哪一列有打勾符号）
        for col_idx, level in severity_columns.items():
            if col_idx < len(cells):
                content = cells[col_idx].get('content', '')
                print(f"  🔍 检查列 {col_idx} ({level}): '{content}'")
                # 检查是否有打勾符号
                if has_check_mark(content):
                    particle['severity_level'] = level
                    print(f"  ✅ 检测到等级 '{level}' 在列 {col_idx}")
                    break
        
        # 提取尺寸
        if size_column is not None and size_column < len(cells):
            size_content = clean_text(cells[size_column].get('content', ''))
            if size_content:
                particle['size_range'] = size_content
                print(f"  📏 提取尺寸: {size_content}")
        
        particles.append(particle)
        print(f"✅ 提取颗粒: {particle}")
    
    return particles


def has_check_mark(content: str) -> bool:
    """检查内容是否包含打勾符号"""
    if not content:
        return False
    
    # 常见的打勾符号和标记
    check_marks = [
        '✓', '✔', '√',  # 勾号
        '■', '●', '◆',  # 实心符号
        '☑', '☒', '☐',  # 复选框
        '[x]', '[X]', '[√]', '[v]', '[V]',  # 方括号标记
        '是', '有', 'Yes', 'YES', 'yes',  # 文字标记
    ]
    
    content = content.strip()
    
    # 直接包含打勾符号
    for mark in check_marks:
        if mark in content:
            return True
    
    # 检查是否包含中文字符（可能是"有"、"是"等）
    if content and len(content) <= 5:
        # 如果内容很短，可能是标记
        return True
    
    return False


def clean_text(text: str) -> str:
    """清理文本"""
    if not text:
        return ''
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 规范化空白
    text = re.sub(r'\s+', ' ', text)
    
    # 移除特殊字符
    text = text.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    
    return text.strip()


# 测试函数
def test_parse_table():
    """测试表格解析"""
    sample_html = """
    <table>
        <tr>
            <th>颗粒类型</th>
            <th>浓度</th>
            <th>尺寸范围</th>
            <th>形貌</th>
        </tr>
        <tr>
            <td>球形颗粒</td>
            <td>15/ml</td>
            <td>5-10μm</td>
            <td>表面光滑</td>
        </tr>
        <tr>
            <td>切削颗粒</td>
            <td>8/ml</td>
            <td>10-20μm</td>
            <td>不规则形状</td>
        </tr>
    </table>
    """
    
    tables = parse_all_tables(sample_html)
    print(f"找到 {len(tables)} 个表格")
    
    particle_table = find_particle_table(tables)
    if particle_table:
        particles = extract_particles_from_table_data(particle_table)
        print(f"提取到 {len(particles)} 个颗粒")
        for p in particles:
            print(f"  - {p}")


if __name__ == '__main__':
    test_parse_table()
