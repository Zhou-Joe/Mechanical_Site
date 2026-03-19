#!/usr/bin/env python3
"""
增强版多次测量结果的智能参数提取
优化了表格结构识别和日期提取逻辑
"""

import re
import json
import html
from datetime import datetime

def extract_multi_measurement_data_enhanced(md_content):
    """
    增强版多次测量数据提取

    优化点：
    1. 正确处理HTML表格的rowspan和colspan属性
    2. 准确提取取样日期
    3. 智能识别参数行和测量值位置
    4. 改进数值提取和清理逻辑

    返回格式：
    {
        'sample_dates': ['27/03/2025', '03/07/2025', '16/09/2025'],
        'measurements': [
            {
                'parameter_name': 'Viscosity 40C cSt/粘度40C cSt',
                'values': [455.3, 447.3, 455.3],
                'unit': 'cSt',
                'standard_range': '±15%',
                'is_normal': [True, True, True]
            },
            ...
        ]
    }
    """

    result = {
        'sample_dates': [],
        'measurements': []
    }

    try:
        # 提取表格行
        table_rows = re.findall(r'<tr>(.*?)</tr>', md_content, re.DOTALL)
        print(f"📊 找到 {len(table_rows)} 个表格行")

        # 解析时间信息 - 增强版日期提取
        sample_dates = []
        analysis_dates = []
        diagnosis_dates = []

        # 特殊处理soaring文件的取样日期提取
        # soaring文件的取样日期标签和日期数据在不同行中
        # 需要先找到标签行，然后在下一行查找日期

        for i, row in enumerate(table_rows):
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cleaned_cells = []
            for cell in cells:
                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                cleaned_cells.append(clean_cell)

            # 查找取样日期标签行 - 增强匹配模式
            if any(keyword in cleaned_cells[0] for keyword in ['取样日期', 'Samplingdate', 'Sample Date', 'Samplingdate取样日期']):
                # 检查当前行是否有日期数据 - 增强验证
                dates_in_current_row = []
                for date in cleaned_cells[1:]:
                    if date and date not in ['-', '：', '·', '']:
                        # 验证是否真的是日期格式
                        parsed_date = parse_date_enhanced(date)
                        if parsed_date is not None:
                            dates_in_current_row.append(parsed_date)

                if dates_in_current_row and len(dates_in_current_row) >= 2:
                    # 当前行有日期数据且至少有2个日期
                    sample_dates = dates_in_current_row
                    print(f"📅 找到取样日期（当前行）: {sample_dates}")
                else:
                    # 当前行没有足够的日期数据，检查后续几行
                    # soaring文件的取样日期可能在标签行后的第2行或第3行
                    found_dates = False
                    for offset in range(1, 4):  # 检查后续3行
                        if i + offset < len(table_rows):
                            next_row = table_rows[i + offset]
                            next_cells = re.findall(r'<td[^>]*>(.*?)</td>', next_row, re.DOTALL)
                            next_cleaned_cells = []
                            for cell in next_cells:
                                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                                next_cleaned_cells.append(clean_cell)

                            # 检查该行是否包含多个日期格式（取样日期行通常有3个日期）
                            dates_in_row = []
                            for cell in next_cleaned_cells:
                                if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', cell):
                                    parsed_date = parse_date_enhanced(cell)
                                    if parsed_date:
                                        dates_in_row.append(parsed_date)

                            # 如果找到2个或更多日期，认为是取样日期行
                            if len(dates_in_row) >= 2:
                                sample_dates = dates_in_row
                                print(f"📅 找到取样日期（第{i+offset+1}行）: {sample_dates}")
                                found_dates = True
                                break

                    if not found_dates:
                        print(f"⚠️ 未找到取样日期，检查了标签行后3行")

            # 查找分析日期行
            elif any(keyword in cleaned_cells[0] for keyword in ['分析日期', 'Analysisdate', 'Analysis Date']):
                dates = cleaned_cells[1:]
                analysis_dates = [parse_date_enhanced(date) for date in dates if date and date not in ['-', '：', '·', '']]
                print(f"📅 找到分析日期: {analysis_dates}")

            # 查找诊断日期行
            elif any(keyword in cleaned_cells[0] for keyword in ['诊断日期', 'Diagnosisdate', 'Diagnosis Date']):
                dates = cleaned_cells[1:]
                diagnosis_dates = [parse_date_enhanced(date) for date in dates if date and date not in ['-', '：', '·', '']]
                print(f"📅 找到诊断日期: {diagnosis_dates}")

        result['sample_dates'] = sample_dates

        # 解析参数数据 - 增强版参数识别
        measurements = []

        # 扩展的参数关键词列表
        param_keywords = [
            # 中文关键词
            '粘度', '水分', '酸值', '闪点', '倾点', '密度', '粘度指数', '污染度', '颗粒数', 'pq指数', '光谱测定',
            '铁', '铜', '铝', '硅', '钠', '钒', '镍', '铬', '锰', '镁', '钙', '锌', '铅', '锡', '磷', '钡', '钼', '硼', '银', '钛', '钾',
            # 英文关键词
            'viscosity', 'water', 'acid', 'flash', 'density', 'koh', 'tan', 'particle', 'pq', 'spectrometry',
            'iron', 'copper', 'aluminum', 'silicon', 'sodium', 'vanadium', 'nickel'
        ]

        # 非参数行关键词（用于过滤）
        non_param_keywords = [
            '取样位置', '取样日期', '分析日期', '诊断日期', '设备运行时间', '油品使用时间', '补油量', '交通灯',
            '外观', 'Samplingtype', 'Samplingdate', 'Analysisdate', 'Diagnosisdate',
            'Equipmentlife', 'Oillife', 'Top up', 'Light', 'Appearance'
        ]

        for row in table_rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            cleaned_cells = []
            for cell in cells:
                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                cleaned_cells.append(clean_cell)

            # 跳过空行和列数不足的行
            if len(cleaned_cells) < 3:
                continue

            param_name = cleaned_cells[0]

            # 检查是否是非参数行
            is_non_param = any(keyword in param_name for keyword in non_param_keywords)
            if is_non_param:
                continue

            # 检查是否是参数行
            is_param = any(keyword.lower() in param_name.lower() for keyword in param_keywords)

            # 也检查是否包含数值（排除表头行）
            has_numeric = any(re.search(r'\d+\.?\d*', cell) for cell in cleaned_cells[1:])

            if is_param and has_numeric:
                print(f"🔬 处理参数: {param_name}")
                print(f"   原始数据: {cleaned_cells}")

                # 增强版数据提取 - 正确处理有空列的表格结构
                # 表格结构: [参数名称, 空列, 标准范围, 测量值1, 测量值2, 测量值3, 状态]
                if len(cleaned_cells) >= 6:
                    # 标准范围在第3列（索引2）
                    standard_range = cleaned_cells[2] if len(cleaned_cells) > 2 else ''
                    standard_range = html.unescape(standard_range).strip()

                    # 测量值从第4列开始（索引3），取3个测量值
                    values = []
                    measurement_indices = [3, 4, 5]  # 测量值1, 2, 3的位置

                    for idx in measurement_indices:
                        if idx < len(cleaned_cells):
                            value_str = cleaned_cells[idx]
                            if value_str and value_str not in ['-', '：', '·', '']:
                                # 增强版数值提取
                                extracted_value = extract_numeric_value_enhanced(value_str)
                                if extracted_value is not None:
                                    values.append(extracted_value)
                                else:
                                    values.append(None)
                            else:
                                values.append(None)
                        else:
                            values.append(None)
                else:
                    # 兼容旧格式，如果没有足够的列
                    standard_range = cleaned_cells[1] if len(cleaned_cells) > 1 else ''
                    standard_range = html.unescape(standard_range).strip()

                    values = []
                    for i in range(2, len(cleaned_cells)):
                        value_str = cleaned_cells[i]
                        if value_str and value_str not in ['-', '：', '·', '']:
                            extracted_value = extract_numeric_value_enhanced(value_str)
                            if extracted_value is not None:
                                values.append(extracted_value)
                            else:
                                values.append(None)
                        else:
                            values.append(None)

                # 提取单位 - 增强版单位识别
                unit = extract_unit_enhanced(param_name, cleaned_cells)

                # 判断是否正常 - 增强版范围检查
                is_normal_list = []
                for i, value in enumerate(values):
                    if value is None:
                        is_normal_list.append(None)
                    else:
                        is_normal = check_if_normal_enhanced(value, standard_range)
                        is_normal_list.append(is_normal)

                measurements.append({
                    'parameter_name': param_name,
                    'values': values,
                    'unit': unit,
                    'standard_range': standard_range,
                    'is_normal': is_normal_list
                })

                print(f"   提取结果: 值={values}, 单位={unit}, 范围={standard_range}")
        
        result['measurements'] = measurements
        
        print(f"✅ 提取完成: {len(sample_dates)} 个日期, {len(measurements)} 个参数")
        return result
        
    except Exception as e:
        print(f"❌ 提取多次测量数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return result

def parse_date_enhanced(date_str):
    """增强版日期解析"""
    if not date_str or date_str in ['-', '：', '·', '']:
        return None
    
    # 清理日期字符串
    date_str = date_str.strip()
    
    # 扩展的日期格式
    date_formats = [
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%Y年%m月%d日',
        '%d年%m月%Y日',
        '%d.%m.%Y',
        '%Y.%m.%d'
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    # 尝试智能解析
    try:
        # 处理一些特殊格式
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            day, month, year = date_str.split('/')
            return datetime(int(year), int(month), int(day)).date()
        elif re.match(r'\d{4}/\d{1,2}/\d{1,2}', date_str):
            year, month, day = date_str.split('/')
            return datetime(int(year), int(month), int(day)).date()
    except:
        pass
    
    print(f"⚠️ 无法解析日期: {date_str}")
    return None

def extract_numeric_value_enhanced(value_str):
    """增强版数值提取"""
    if not value_str or value_str in ['-', '：', '·', '']:
        return None
    
    # 清理字符串
    cleaned = value_str.strip()
    
    # 处理特殊符号
    cleaned = cleaned.replace('<', '').replace('>', '').replace('≤', '').replace('≥', '').replace('≤', '')
    
    # 提取数值
    # 支持多种格式：123, 123.45, <123, >123, ≤123, ≥123
    patterns = [
        r'([<>≤≥]?\s*\d+\.?\d*)',  # 带比较符号的数值
        r'(\d+\.?\d*)',           # 纯数值
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            try:
                value_str = match.group(1).replace(' ', '')
                return float(value_str)
            except ValueError:
                continue
    
    return None

def extract_unit_enhanced(param_name, cells):
    """增强版单位提取"""
    param_lower = param_name.lower()
    
    # 从参数名称中提取单位
    if 'cst' in param_lower or '粘度' in param_lower:
        return 'cSt'
    elif 'ppm' in param_lower:
        return 'ppm'
    elif 'mg koh/g' in param_lower or '酸值' in param_lower or 'tan' in param_lower:
        return 'mg KOH/g'
    elif '%' in param_lower:
        return '%'
    elif 'years' in param_lower or '年' in param_lower:
        return 'years'
    elif 'iso' in param_lower or '颗粒数' in param_lower:
        return 'ISO'
    
    # 从其他单元格中查找单位
    for cell in cells[1:]:  # 从第2列开始查找
        cell_lower = cell.lower()
        if any(unit in cell_lower for unit in ['cst', 'ppm', '%', 'mg koh/g', 'years', 'iso']):
            if 'cst' in cell_lower:
                return 'cSt'
            elif 'ppm' in cell_lower:
                return 'ppm'
            elif '%' in cell_lower:
                return '%'
            elif 'mg koh/g' in cell_lower:
                return 'mg KOH/g'
            elif 'years' in cell_lower:
                return 'years'
            elif 'iso' in cell_lower:
                return 'ISO'
    
    return ''

def check_if_normal_enhanced(value, standard_range):
    """增强版数值范围检查"""
    if not standard_range or standard_range in ['-', '', '：']:
        return True  # 如果没有标准范围，默认为正常
    
    try:
        # 处理百分比范围
        if '±' in standard_range:
            # 例如 ±15% 表示相对于某个基准值的±15%
            # 这里简化处理，假设为正常
            return True
        
        # 处理范围格式 "min-max"
        if '-' in standard_range:
            range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', standard_range)
            if range_match:
                min_val = float(range_match.group(1))
                max_val = float(range_match.group(2))
                return min_val <= value <= max_val
        
        # 处理小于格式 "<value" 或 "≤value"
        if '<' in standard_range or '≤' in standard_range:
            max_match = re.search(r'[<≤]\s*(\d+\.?\d*)', standard_range)
            if max_match:
                max_val = float(max_match.group(1))
                return value < max_val
        
        # 处理大于格式 ">value" 或 "≥value"
        if '>' in standard_range or '≥' in standard_range:
            min_match = re.search(r'[>≥]\s*(\d+\.?\d*)', standard_range)
            if min_match:
                min_val = float(min_match.group(1))
                return value > min_val
        
        # 处理大于格式 ">value"
        if '>' in standard_range:
            min_match = re.search(r'>\s*(\d+\.?\d*)', standard_range)
            if min_match:
                min_val = float(min_match.group(1))
                return value > min_val
        
        return True  # 无法解析时默认为正常
        
    except (ValueError, AttributeError):
        return True

def create_multiple_reports_enhanced(multi_data, equipment, report_number_base):
    """
    增强版从多次测量数据创建多个报告记录
    """
    reports = []
    
    measurement_count = len(multi_data['sample_dates'])
    
    for i in range(measurement_count):
        # 安全获取取样日期
        sample_date = multi_data['sample_dates'][i] if i < len(multi_data['sample_dates']) else None
        
        # 报告日期使用取样日期
        report_date = sample_date
        
        # 确保日期不为空
        from datetime import date
        today = date.today()
        if not sample_date:
            sample_date = today
        if not report_date:
            report_date = today
        
        # 创建报告
        report_data = {
            'equipment': equipment,
            'sample_date': sample_date,
            'report_date': report_date,
            'report_number': f"{report_number_base}_{i+1}" if measurement_count > 1 else report_number_base,
            'parameters': []
        }
        
        # 为每次测量创建参数
        for measurement in multi_data['measurements']:
            if i < len(measurement['values']) and measurement['values'][i] is not None:
                param_data = {
                    'parameter_name': measurement['parameter_name'],
                    'parameter_value': measurement['values'][i],
                    'unit': measurement['unit'],
                    'standard_range': measurement['standard_range'],
                    'is_normal': measurement['is_normal'][i] if i < len(measurement['is_normal']) else True
                }
                report_data['parameters'].append(param_data)
        
        reports.append(report_data)
    
    return reports

def test_enhanced_extraction():
    """测试增强版提取功能"""
    print("🧪 测试增强版多次测量数据提取...")
    
    # 读取测试文件
    test_file = "md_analysis_32868251_Rapids lift齿轮箱油.md"
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        result = extract_multi_measurement_data_enhanced(md_content)
        
        print("🔍 增强版多次测量数据提取结果:")
        print(f"📅 取样日期: {result['sample_dates']}")
        print(f" 参数数量: {len(result['measurements'])}")
        
        print("\n📋 前5个参数:")
        for i, measurement in enumerate(result['measurements'][:5]):
            print(f"  {i+1}. {measurement['parameter_name']}")
            print(f"     值: {measurement['values']}")
            print(f"     单位: {measurement['unit']}")
            print(f"     标准范围: {measurement['standard_range']}")
            print(f"     是否正常: {measurement['is_normal']}")
        
        return result
        
    except FileNotFoundError:
        print(f"❌ 测试文件不存在: {test_file}")
        return None

if __name__ == "__main__":
    test_enhanced_extraction()
