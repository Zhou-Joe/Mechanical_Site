"""
Downtime Details Report Generator - Splunk Version
直接从 Splunk 拉取数据生成停机详情报告
"""

import sys
import os
import re
import time
import csv
import io
import requests
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import Dict, Any, List, Tuple

# 添加 Downtime_Chart 目录到路径以复用工具模块
DOWNTIME_CHART_DIR = os.path.join(os.path.dirname(__file__), '..', 'Downtime_Chart')
sys.path.insert(0, DOWNTIME_CHART_DIR)

# 先加载 .env 文件，再导入 tools_splunk
from dotenv import load_dotenv
env_path = os.path.join(DOWNTIME_CHART_DIR, '.env')
load_dotenv(env_path)

from tools_splunk import run_splunk_job


def fetch_data_from_splunk(start_date: str, end_date: str) -> Tuple[List[Dict], List[Dict]]:
    """
    从 Splunk 获取停机数据

    参数:
        start_date: 开始日期，格式 "YYYY-MM-DD"
        end_date: 结束日期，格式 "YYYY-MM-DD"

    返回:
        tuple: (data_101, data_105) 两个字典列表
    """
    print(f"\n从 Splunk 获取数据: {start_date} 到 {end_date}")

    # 构建 Splunk 查询 - 使用 artdowntime 命令获取数据
    spl = f'| artdowntime startdate="{start_date}" enddate="{end_date}" | table _time attractions datetime down_time workorder downtime_summary downtime_details dt_hour mclass fct_downtime_type week_ending | rex field=downtime_summary "(?<type>\\d\\d\\d+)"'

    # 执行 Splunk 查询
    result = run_splunk_job(spl, max_rows=50000)

    if result['status'] != 'success':
        raise Exception(f"Splunk 查询失败: {result.get('error', 'Unknown error')}")

    rows = result.get('preview_csv', '')
    if not rows:
        print("警告: 没有从 Splunk 获取到数据")
        return [], []

    # 解析 CSV 数据
    from io import StringIO
    import csv

    csv_reader = csv.DictReader(StringIO(rows))
    all_data = list(csv_reader)

    print(f"成功获取 {len(all_data)} 条记录")

    # 调试：打印所有 fct_downtime_type 的唯一值
    fct_types = set(row.get('fct_downtime_type', '') for row in all_data)
    print(f"fct_downtime_type 类型: {fct_types}")

    # 分离 101 和 105 数据（显示所有 fct_downtime_type）
    data_101 = []
    data_105 = []

    for row in all_data:
        # 根据 type 字段区分 101 和 105（处理字符串和数字类型）
        type_val = row.get('type', '')
        # 转换为字符串进行比较，处理 '101', 101, '101.0', 101.0 等情况
        type_str = str(type_val).strip()
        if type_str in ['101', '100', '101.0', '100.0']:
            data_101.append(row)
        elif type_str in ['105', '105.0']:
            data_105.append(row)

    print(f"101 数据: {len(data_101)} 条记录")
    print(f"105 数据: {len(data_105)} 条记录")

    return data_101, data_105


def parse_attraction(attractions_str: str) -> Tuple[str, str]:
    """
    解析设施字符串，提取 ID 和名称

    参数:
        attractions_str: 设施字符串，如 "301 - Jet Packs"

    返回:
        tuple: (attraction_id, attraction_name)
    """
    if not attractions_str:
        return '', ''

    # 尝试匹配 "ID - Name" 格式
    match = re.match(r'(.+?)\s+-\s+(.+)', attractions_str.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # 如果没有匹配到，整个字符串作为名称
    return '', attractions_str.strip()


def format_datetime(dt_str: str) -> str:
    """
    格式化日期时间字符串

    参数:
        dt_str: 原始日期时间字符串

    返回:
        格式化后的字符串，如 "1/8/2026 13:04"
    """
    if not dt_str:
        return ''

    try:
        # 尝试多种格式
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M', '%m/%d/%Y %H:%M:%S']:
            try:
                dt = datetime.strptime(dt_str.strip(), fmt)
                return dt.strftime('%m/%d/%Y %H:%M')
            except ValueError:
                continue

        # 如果都失败了，返回原字符串
        return dt_str
    except:
        return dt_str


def format_down_time(down_time_str: str, duration_hours: float = 0) -> str:
    """
    格式化停机时间字符串，只显示 Down 和 Up 时间（不含日期）
    Up 时间根据 Down + Duration 计算

    参数:
        down_time_str: 原始时间字符串，格式为 "开始时间\n结束时间\n持续时间"
        duration_hours: 持续时间（小时）

    返回:
        格式化后的 HTML 字符串，格式为 "Down时间<br>Up时间"
    """
    if not down_time_str:
        return ''

    # 处理换行符
    parts = re.split(r'[\n\r]+', down_time_str.strip())
    if len(parts) < 1:
        return ''

    # 提取 Down 时间（第一行）
    down_time_full = parts[0].strip()

    # 尝试解析 Down 时间，提取时间部分
    down_time_only = down_time_full
    down_datetime = None

    # 尝试多种格式解析
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%m/%d/%Y %H:%M', '%m/%d/%Y %H:%M:%S', '%H:%M', '%H:%M:%S']:
        try:
            down_datetime = datetime.strptime(down_time_full, fmt)
            # 如果只包含时间，使用当前日期
            down_time_only = down_datetime.strftime('%H:%M')
            break
        except ValueError:
            continue

    # 如果没有成功解析，尝试从字符串中提取时间部分 (HH:MM)
    if down_datetime is None:
        time_match = re.search(r'(\d{1,2}):(\d{2})', down_time_full)
        if time_match:
            down_time_only = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

    # 计算 Up 时间
    up_time_only = ''
    if down_datetime is not None and duration_hours:
        # 将 duration（小时）转换为 timedelta
        duration_td = timedelta(hours=float(duration_hours))
        up_datetime = down_datetime + duration_td
        up_time_only = up_datetime.strftime('%H:%M')
    elif len(parts) >= 2:
        # 如果无法计算，尝试从原始数据中提取 Up 时间
        up_time_full = parts[1].strip()
        time_match = re.search(r'(\d{1,2}):(\d{2})', up_time_full)
        if time_match:
            up_time_only = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"

    # 返回格式：Down时间<br>Up时间
    if up_time_only:
        return f"{down_time_only}<br>{up_time_only}"
    return down_time_only


def extract_root_cause(downtime_details: str) -> str:
    """
    从停机详情中提取根本原因
    如果 20- 的内容是 "Maintenance related" 或 "Maint related"，则返回 10- 的内容

    参数:
        downtime_details: 停机详情文本

    返回:
        根本原因文本
    """
    if not downtime_details:
        return ''

    # 提取 10- 和 20- 的内容
    content_10 = ''
    content_20 = ''

    match_10 = re.search(r'10\s*-\s*(.+?)(?:\n|$)', downtime_details)
    if match_10:
        content_10 = match_10.group(1).strip()

    match_20 = re.search(r'20\s*-\s*(.+?)(?:\n|$)', downtime_details)
    if match_20:
        content_20 = match_20.group(1).strip()

    # 如果 20- 是 Maintenance related 或 Maint related，返回 10- 的内容
    if content_20 and ('maintenance related' in content_20.lower() or 'maint related' in content_20.lower()):
        return content_10

    # 否则返回 20- 的内容
    return content_20


def extract_duration(down_time_str: str) -> str:
    """
    从 down_time 字段中提取持续时间（第三行）

    参数:
        down_time_str: 原始时间字符串，格式为 "开始时间\n结束时间\n持续时间"

    返回:
        持续时间字符串
    """
    if not down_time_str:
        return ''

    # 处理可能的 <br> 标签或换行符
    # 先替换 <br> 为换行符，然后分割
    normalized = down_time_str.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    parts = re.split(r'[\n\r]+', normalized.strip())
    if len(parts) >= 3:
        return parts[2]  # 返回第三行（持续时间）
    return ''


def format_downtime_detail(downtime_details: str) -> str:
    """
    格式化停机详情，按 10-, 20-, 30-, 40- 分段显示

    参数:
        downtime_details: 原始停机详情文本

    返回:
        格式化后的 HTML 字符串
    """
    if not downtime_details:
        return ''

    # 按行分割
    lines = re.split(r'[\n\r]+', downtime_details.strip())

    formatted_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检查是否以数字开头（如 "10 -", "10-"）
        match = re.match(r'^(\d+)\s*-\s*(.*)', line)
        if match:
            num = match.group(1)
            content = match.group(2).strip()
            formatted_lines.append(f"{num} - {content}")
        else:
            # 如果不是标准格式，直接添加
            formatted_lines.append(line)

    # 用 <br> 连接所有行
    return '<br>'.join(formatted_lines)


def process_data_for_report(data: List[Dict], code: str) -> List[Dict]:
    """
    处理数据为报告格式

    参数:
        data: 原始数据列表
        code: 停机代码 ('101' 或 '105')

    返回:
        处理后的数据列表
    """
    processed = []

    for row in data:
        attraction_id, attraction_name = parse_attraction(row.get('attractions', ''))

        # 对于 Soaring 的设施，格式化为 "Soaring Over the Horizon (Ride A)"
        if 'Soaring' in attraction_name and attraction_id in ['Ride A', 'Ride B']:
            attraction_name = f"{attraction_name} ({attraction_id})"

        # 先获取原始 duration 值（不 round），用于计算 Up 时间
        duration_raw = float(row.get('dt_hour', 0)) if row.get('dt_hour') else 0
        # 使用原始值计算 Down/Up 时间，确保精确
        down_up_dur = format_down_time(row.get('down_time', ''), duration_raw)
        # 然后 round 用于显示
        duration_val = round(duration_raw, 2)

        processed_row = {
            'attraction_id': attraction_id,
            'attraction_name': attraction_name,
            'attraction_full': f"{attraction_id} - {attraction_name}" if attraction_id else attraction_name,
            'report_date': format_datetime(row.get('datetime', '')),
            'down_up_dur': down_up_dur,
            'duration': duration_val,  # Duration 来自 dt_hour 列，保留2位小数
            'work_order': row.get('workorder', ''),
            'reason_code': row.get('mclass', ''),
            'downtime_summary': row.get('downtime_summary', ''),  # 添加 downtime_summary 列
            'downtime_detail': format_downtime_detail(row.get('downtime_details', '')),  # 格式化 downtime_detail 显示
            'root_cause': extract_root_cause(row.get('downtime_details', '')),
            'down_code': code,
            'maint': 'Y' if row.get('fct_downtime_type') == 'Maintenance' else 'N',  # 只有 Maintenance 类型才显示 Y
            'fct_downtime_type': row.get('fct_downtime_type', ''),  # 添加 downtime_type 用于判断标黄
            'has_investigation': 'investigation' in row.get('downtime_details', '').lower(),  # 检测是否包含 investigation
        }

        processed.append(processed_row)

    return processed


def group_by_attraction(data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按设施分组数据

    参数:
        data: 处理后的数据列表

    返回:
        按设施名称分组的字典
    """
    grouped = {}

    for row in data:
        attraction_name = row['attraction_full']
        if attraction_name not in grouped:
            grouped[attraction_name] = []
        grouped[attraction_name].append(row)

    # 对每个设施内的记录按日期排序
    for attraction in grouped:
        grouped[attraction].sort(key=lambda x: x['report_date'])

    return grouped


def generate_html_report(data: List[Dict], code: str, week_info: str = '') -> str:
    """
    生成 HTML 报告

    参数:
        data: 处理后的数据列表
        code: 停机代码 ('101' 或 '105')
        week_info: 周信息字符串

    返回:
        HTML 字符串
    """
    grouped = group_by_attraction(data)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Downtime Report - {code}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            background-color: #f2f2f2;
            position: sticky;
            top: 0;
        }}
        .attraction {{
            font-size: 25px;
            font-weight: bold;
        }}
        .root-cause {{
            font-size: 25px;
            font-weight: bold;
            background-color: #ffff99;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        h1 {{
            color: #333;
        }}
        .no-root-cause {{
            background-color: transparent;
            font-weight: normal;
            font-size: 14px;
        }}
        .attraction-group {{
            border-top: 3px solid #333;
        }}
    </style>
</head>
<body>
    <h1>Downtime Report -- {code}</h1>
    <table>
        <thead>
            <tr>
                <th>Report Date</th>
                <th>Down / Up</th>
                <th>Duration</th>
                <th>Work Order</th>
                <th>Reason / Code</th>
                <th>Downtime Summary</th>
                <th>Downtime Detail</th>
                <th>Root Cause</th>
                <th>Down Code</th>
                <th>Maint</th>
            </tr>
        </thead>
        <tbody>'''

    # 生成表格内容
    first_attraction = True
    for attraction_name, records in grouped.items():
        # 添加空行和设施标题
        if not first_attraction:
            html += '<tr><td colspan="10">  </td></tr>'
        first_attraction = False

        # 检查是否需要标黄：Maintenance 类型且有 root_cause，或者包含 investigation
        has_maintenance_root_cause = any(
            r['root_cause'] and r.get('maint') == 'Y'
            for r in records
        )
        has_investigation = any(r.get('has_investigation') for r in records)
        needs_highlight = has_maintenance_root_cause or has_investigation
        bg_style = ' style="background-color: #ffff99"' if needs_highlight else ''

        html += f'<tr class="attraction"{bg_style}><td colspan="10">{attraction_name}</td></tr>'

        # 添加该设施的所有记录
        for record in records:
            # 确定 root cause 显示内容
            if record.get('has_investigation'):
                # 如果包含 investigation，root cause 显示 "Investigation"
                root_cause_class = 'root-cause'
                root_cause_text = 'Investigation'
            elif record.get('maint') == 'Y':
                # 只有 Maintenance 类型（Maint=Y）才显示 root cause
                root_cause_class = 'root-cause' if record['root_cause'] else 'no-root-cause'
                root_cause_text = record['root_cause'] if record['root_cause'] else ''
            else:
                root_cause_class = 'no-root-cause'
                root_cause_text = ''

            html += f'''
            <tr class="attraction-group">
                <td>{record['report_date']}</td>
                <td>{record['down_up_dur']}</td>
                <td>{record['duration']}</td>
                <td>{record['work_order']}</td>
                <td>-<br>{record['reason_code']}<br>-<br>-</td>
                <td>{record['downtime_summary']}</td>
                <td>{record['downtime_detail']}</td>
                <td class="{root_cause_class}">
                {root_cause_text}
                </td>
                <td>{record['down_code']}</td>
                <td>{record['maint']}</td>
            </tr>'''

    html += '''
        </tbody>
    </table>
</body>
</html>'''

    return html


def get_week_range(weeks_ago: int = 1) -> Tuple[str, str]:
    """
    获取指定周的起止日期

    参数:
        weeks_ago: 几周前，默认 1 表示上周

    返回:
        tuple: (start_date, end_date) 格式 "YYYY-MM-DD"
    """
    today = datetime.now()

    # 找到上周一（上周开始）
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7 * weeks_ago)
    last_sunday = last_monday + timedelta(days=6)

    return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate Downtime Detail Report from Splunk')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--weeks-ago', type=int, default=1, help='Weeks ago to report (default: 1)')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory for HTML files')

    args = parser.parse_args()

    # 确定日期范围
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        start_date, end_date = get_week_range(args.weeks_ago)

    print(f"生成报告: {start_date} 到 {end_date}")

    try:
        # 从 Splunk 获取数据
        data_101, data_105 = fetch_data_from_splunk(start_date, end_date)

        # 处理数据
        processed_101 = process_data_for_report(data_101, '101')
        processed_105 = process_data_for_report(data_105, '105')

        # 生成周信息字符串
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        week_info = f"{start_dt.strftime('%m/%d/%Y')} - {end_dt.strftime('%m/%d/%Y')}"

        # 生成 HTML 报告
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名
        start_str = start_dt.strftime('%Y%m%d')
        end_str = end_dt.strftime('%Y%m%d')

        html_101 = generate_html_report(processed_101, '101', week_info)
        output_101 = os.path.join(output_dir, f'Weekly_Downtime_Report_101_{start_str}_{end_str}.html')
        with open(output_101, 'w', encoding='utf-8') as f:
            f.write(html_101)
        print(f"101 报告已生成: {output_101}")

        html_105 = generate_html_report(processed_105, '105', week_info)
        output_105 = os.path.join(output_dir, f'Weekly_Downtime_Report_105_{start_str}_{end_str}.html')
        with open(output_105, 'w', encoding='utf-8') as f:
            f.write(html_105)
        print(f"105 报告已生成: {output_105}")

        print("\n报告生成完成!")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
