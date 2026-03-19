"""
Downtime Chart 分析模块
集成停机报告生成功能到 Django 项目
"""

import pandas as pd
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 将 Downtime_Chart 目录添加到路径
downtime_chart_path = Path(__file__).resolve().parent.parent / 'Downtime_Chart'
if str(downtime_chart_path) not in sys.path:
    sys.path.insert(0, str(downtime_chart_path))

# 加载 .env 文件
env_path = downtime_chart_path / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path))

# 导入 Downtime_Chart 模块中的功能
from predict_downtime_type import DowntimeTypePredictor
from tools_splunk import run_splunk_job

# 全局变量存储预测器实例
_predictor = None


def get_predictor():
    """获取或初始化预测器实例"""
    global _predictor
    if _predictor is None:
        model_path = downtime_chart_path / 'roberta_downtime_model'
        _predictor = DowntimeTypePredictor(str(model_path))
    return _predictor


def fetch_data_from_splunk(start_date, end_date):
    """
    从Splunk获取停机数据
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    
    返回:
    tuple: (df_101, df_105) 两个DataFrame，分别对应101和105数据
    """
    # 构建Splunk查询 - 添加rex字段提取事件类型(101/105)
    spl = f'| artdowntime startdate="{start_date}" enddate="{end_date}" | table _time attractions datetime down_time workorder downtime_summary downtime_details dt_hour mclass fct_downtime_type week_ending | rex field=downtime_summary "(?<type>\\d\\d\\d+)"'
    
    # 执行Splunk查询
    result = run_splunk_job(spl, max_rows=50000)
    
    if result['status'] != 'success':
        raise Exception(f"Splunk查询失败: {result.get('error', 'Unknown error')}")
    
    # 将结果转换为DataFrame
    rows = result['preview_csv']
    if rows:
        from io import StringIO
        df = pd.read_csv(StringIO(rows))
        
        # 只保留 Maintenance 类型的记录
        if 'fct_downtime_type' in df.columns:
            df = df[df['fct_downtime_type'] == 'Maintenance'].copy()
    else:
        df = pd.DataFrame()
    
    # 分离101和105数据
    if not df.empty:
        if 'type' in df.columns:
            # 100和101都是downtime数据，发送到chart 1
            df_101 = df[(df['type'] == '101') | (df['type'] == 101) | (df['type'] == '100') | (df['type'] == 100)].copy()
            df_105 = df[(df['type'] == '105') | (df['type'] == 105)].copy()
        else:
            # 如果没有type列，默认全部作为101处理
            df_101 = df.copy()
            df_105 = pd.DataFrame()
    else:
        df_101 = pd.DataFrame()
        df_105 = pd.DataFrame()
    
    return df_101, df_105


def process_splunk_data_to_format(df, downtime_type):
    """
    将Splunk数据转换为期望的格式
    
    参数:
    df (pandas.DataFrame): 从Splunk获取的原始数据
    downtime_type (str): 停机类型 ('101' 或 '105')
    
    返回:
    pandas.DataFrame: 转换后的DataFrame
    """
    if df.empty:
        return df
    
    # 映射Splunk列名到期望的列名
    df_transformed = pd.DataFrame()
    df_transformed['Attraction'] = df['attractions'].apply(lambda x: f"Attraction: {x}" if pd.notna(x) else '')
    df_transformed['Down_Code'] = downtime_type
    df_transformed['Maint'] = 'Y'
    df_transformed['Report_Date'] = df['datetime'].apply(lambda x: pd.to_datetime(x).strftime('%m/%d/%Y %H:%M') if pd.notna(x) else '')
    df_transformed['Down_Up_Dur'] = df['down_time'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Work_Order'] = df['workorder'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Reason_Code'] = ''
    df_transformed['Operations'] = ''
    df_transformed['Category'] = df['mclass'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Date_Time'] = df['datetime'].apply(lambda x: pd.to_datetime(x).strftime('%m/%d/%Y %H:%M') if pd.notna(x) else '')
    df_transformed['Time_Range'] = df['down_time'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Work_Order_Details'] = df['workorder'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Reason_Details'] = df['downtime_summary'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['Unnamed'] = ''
    df_transformed['Classification_Details'] = df['downtime_details'].apply(lambda x: str(x) if pd.notna(x) else '')
    df_transformed['dt_hour'] = df['dt_hour'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
    df_transformed['Code'] = 101 if downtime_type == '101' else 105
    df_transformed['Y_N'] = 'Y'
    
    # 提取设施名称中的编号和名称
    def extract_attraction_id(attraction_str):
        """提取设施ID"""
        try:
            if pd.isna(attraction_str):
                return ''
            attraction_str = str(attraction_str).strip()
            if attraction_str == '':
                return ''
            if 'Attraction:' in attraction_str and ' - ' in attraction_str:
                parts = attraction_str.split(' - ', 1)
                if len(parts) == 2:
                    return parts[0].replace('Attraction:', '').strip()
            return ''
        except Exception:
            return ''
    
    def extract_attraction_name(attraction_str):
        """提取设施名称"""
        try:
            if pd.isna(attraction_str):
                return ''
            attraction_str = str(attraction_str).strip()
            if attraction_str == '':
                return ''
            if 'Attraction:' in attraction_str:
                clean_str = attraction_str.replace('Attraction:', '').strip()
                if ' - ' in clean_str:
                    return clean_str.split(' - ', 1)[1].strip()
                return clean_str
            return attraction_str
        except Exception:
            return ''
    
    # 提取ID和Name
    df_transformed['Attraction_ID'] = df_transformed['Attraction'].apply(extract_attraction_id)
    df_transformed['Attraction_Name'] = df_transformed['Attraction'].apply(extract_attraction_name)
    
    # 对于 Soaring 的设施，格式化为 "Soaring Over the Horizon (Ride A)" 或 "Soaring Over the Horizon (Ride B)"
    def format_attraction_name(row):
        attraction_id = row['Attraction_ID'] if pd.notna(row['Attraction_ID']) else ''
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) else ''
        
        if 'Soaring' in attraction_name and attraction_id in ['Ride A', 'Ride B']:
            return f"{attraction_name} ({attraction_id})"
        else:
            return attraction_name
    
    df_transformed['Attraction_Name'] = df_transformed.apply(format_attraction_name, axis=1)
    
    # 转换Code列为整数
    df_transformed['Code'] = df_transformed['Code'].astype('Int64')
    
    return df_transformed


def classify_downtime_events_with_roberta(df):
    """
    使用roberta模型对停机事件进行分类
    
    参数:
    df (pandas.DataFrame): 包含停机事件的DataFrame
    
    返回:
    pandas.DataFrame: 添加了分类结果的DataFrame
    """
    predictor = get_predictor()
    
    # 添加分类结果列
    df = df.copy()
    df.loc[:, 'Predicted_Category'] = ""
    
    # 对每个事件进行分类
    for idx, row in df.iterrows():
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) else ''
        classification_details = row['Classification_Details'] if pd.notna(row['Classification_Details']) else ''
        category = row['Category'] if pd.notna(row['Category']) else ''
        
        # 组合文本用于预测
        description = f"{classification_details} {category}"
        
        # 使用roberta模型进行预测
        try:
            result = predictor.predict(attraction_name, description)
            predicted_category = result['predicted_class']
        except Exception:
            # 如果预测失败，则使用默认分类
            ride_related_keywords = ['ride', 'attraction', 'vehicle', 'track', 'train']
            show_related_keywords = ['show', 'performance', 'theater', 'stage']
            
            is_ride_related = any(keyword in (attraction_name + ' ' + category).lower() for keyword in ride_related_keywords)
            is_show_related = any(keyword in (attraction_name + ' ' + category).lower() for keyword in show_related_keywords)
            
            if is_ride_related:
                predicted_category = 'RideMech'
            elif is_show_related:
                predicted_category = 'ShowMech'
            else:
                predicted_category = 'Facility'
        
        df.loc[idx, 'Predicted_Category'] = predicted_category
    
    return df


def fetch_mri_from_splunk(start_date, end_date):
    """
    从Splunk自动计算MRI值
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    
    返回:
    float: MRI 值
    """
    import datetime as dt_module
    
    # 将日期转换为Unix epoch时间戳
    start_dt = dt_module.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = dt_module.datetime.strptime(end_date, "%Y-%m-%d")
    
    # 转换为epoch时间戳（秒）
    start_epoch = str(int(start_dt.timestamp()))
    end_epoch = str(int(end_dt.timestamp() + 86399))  # +86399秒 = 23:59:59
    
    # 构建Splunk查询
    spl = f'''| artdowntime startdate="{start_date}" enddate="{end_date}"
| search fct_downtime_type=Maintenance downtime_summary!=105* 
| append 
    [| artdowntime startdate="{start_date}" enddate="{end_date}" 
    | search attractions=*Once* OR attractions=*Realm* fct_downtime_type=Maintenance] 
 |stats sum(dt_hour) as s by week_ending
| join week_ending type=left 
    [ search index=ops_time earliest="{start_epoch}" latest="{end_epoch}"|table attrname duration week_ending|search attrname!="*iron-man*"|stats sum(duration) as t by week_ending
    ]
    | fillnull t value=1500
|eval mri=round((1-(s)/(t+28*1+10))*100,1)
| table week_ending mri|sort week_ending desc'''
    
    # 执行Splunk查询
    result = run_splunk_job(spl)
    
    if result['status'] != 'success':
        raise Exception(f"Splunk MRI查询失败: {result.get('error', 'Unknown error')}")
    
    # 将结果转换为DataFrame
    rows = result['preview_csv']
    if rows:
        from io import StringIO
        df = pd.read_csv(StringIO(rows))
        if not df.empty and 'mri' in df.columns:
            mri_value = df.iloc[0]['mri']
            return float(mri_value)
    
    return 95.0  # 默认值


def generate_downtime_chart_html(df_101, df_105, mri_value):
    """
    生成停机报告HTML内容
    
    参数:
    df_101 (pandas.DataFrame): 101数据集
    df_105 (pandas.DataFrame): 105数据集
    mri_value (float): MRI值
    
    返回:
    str: HTML内容
    """
    # 定义所有景点名称
    all_attractions = [
        'Buzz Lightyear Planet Rescue',
        'Camp Discovery - Challenge Trails',
        'Dumbo The Flying Elephant',
        'Fantasia Carousel',
        'Hunny Pot Spin',
        'Junior Explorers Camp',
        'Jet Pack',
        'Once Upon a Time Adventure',
        'Peter Pan\'s Flight',
        'Pirates of Caribbean: Battle for the Sunken Treasure',
        'Rex\'s Racer',
        'Roaring Rapids',
        'Seven Dwarfs Mine Train',
        'Slinky Dog Spin',
        'Soaring Over the Horizon (Ride A)',
        'Soaring Over the Horizon (Ride B)',
        'Stitch Encounter',
        'The Many Adventures of Winnie the Pooh',
        'Tron Lightcycle Power Run',
        'Voyage to the Crystal Grotto',
        'Walt Disney Grand Theatre',
        'Woody\'s Roundup',
        'El Teatro Fandango',
        'Tron Realm Chevrolet Challenge',
        'Zootopia Hot Pursuit'
    ]
    
    # 创建名称映射表
    attraction_name_mapping = {
        '"""Once Upon a Time"" Adventure': 'Once Upon a Time Adventure',
        'Buzz Lightyear Planet Rescue': 'Buzz Lightyear Planet Rescue',
        'Camp Discovery - Challenge Trails': 'Camp Discovery - Challenge Trails',
        'Dumbo the Flying Elephant': 'Dumbo The Flying Elephant',
        'EI Teatro Fandango': 'El Teatro Fandango',
        'Fantasia Carousel': 'Fantasia Carousel',
        'Hunny Pot Spin': 'Hunny Pot Spin',
        'Jet Packs': 'Jet Pack',
        'Junior Explorers Camp': 'Junior Explorers Camp',
        'Peter Pan\'s Flight': 'Peter Pan\'s Flight',
        'Pirates of the Caribbean - Battle for the Sunken Treasure': 'Pirates of the Caribbean: Battle for the Sunken Treasure',
        'Rex\'s Racer': 'Rex\'s Racer',
        'Roaring Rapids': 'Roaring Rapids',
        'Seven Dwarfs Mine Train': 'Seven Dwarfs Mine Train',
        'Slinky Dog Spin': 'Slinky Dog Spin',
        'Soaring Over the Horizon (Ride A)': 'Soaring Over the Horizon (Ride A)',
        'Soaring Over the Horizon (Ride B)': 'Soaring Over the Horizon (Ride B)',
        'Stitch Encounter': 'Stitch Encounter',
        'TRON Lightcycle Power Run': 'Tron Lightcycle Power Run',
        'TRON Realm: Chevrolet Digital Challenge': 'Tron Realm Chevrolet Challenge',
        'The Many Adventures of Winnie the Pooh': 'The Many Adventures of Winnie the Pooh',
        'Voyage to the Crystal Grotto': 'Voyage to the Crystal Grotto',
        'Walt Disney Grand Theatre': 'Walt Disney Grand Theatre',
        'Woody\'s Round-up': 'Woody\'s Roundup',
        'Zootopia Hot Pursue': 'Zootopia Hot Pursuit',
        'El Teatro Fandango': 'El Teatro Fandango',
        'Tron Realm Chevrolet Challenge': 'Tron Realm Chevrolet Challenge',
        'Pirates of the Caribbean - Battle for the Sunken Treasure': 'Pirates of Caribbean: Battle for the Sunken Treasure',
        'Dumbo the Flying Elephant': 'Dumbo The Flying Elephant',
        'Battle for the Sunken Treasure': 'Pirates of Caribbean: Battle for the Sunken Treasure',
        'Soaring Over Horizon (Ride A)': 'Soaring Over the Horizon (Ride A)',
        'Soaring Over Horizon (Ride B)': 'Soaring Over the Horizon (Ride B)',
    }
    
    def normalize_attraction_name(name):
        """将设施名称标准化为图表中使用的名称"""
        if pd.isna(name) or name == '':
            return None
        
        name = str(name).strip()
        
        if name in attraction_name_mapping:
            return attraction_name_mapping[name]
        
        normalized = name.lower().replace('-', ' ').replace('_', ' ')
        
        for splunk_name, standard_name in attraction_name_mapping.items():
            splunk_normalized = splunk_name.lower().replace('-', ' ').replace('_', ' ')
            if normalized == splunk_normalized:
                return standard_name
        
        return name
    
    # 定义停机类别和颜色
    categories = [
        {'name': 'RideMech', 'label': 'Ride Mechanical', 'color': 'rgba(255, 0, 0, 0.7)'},
        {'name': 'RideControl', 'label': 'Ride Control', 'color': 'rgba(0, 255, 0, 0.7)'},
        {'name': 'ShowMech', 'label': 'Show Mechanical', 'color': 'rgba(0, 0, 255, 0.7)'},
        {'name': 'ShowControl', 'label': 'Show Control', 'color': 'rgba(255, 105, 203, 0.7)'},
        {'name': 'Facility', 'label': 'Facility', 'color': 'rgba(153, 102, 255, 0.7)'}
    ]
    
    # 解析停机时长
    def parse_downtime_duration(dt_hour):
        """从dt_hour列提取停机时长（小时）"""
        try:
            if pd.isna(dt_hour) or dt_hour == '':
                return 0.0
            return float(dt_hour)
        except:
            return 0.0
    
    # 为DataFrame添加停机时长列
    if not df_101.empty:
        df_101.loc[:, 'Downtime_Hours'] = df_101['dt_hour'].apply(parse_downtime_duration)
    if not df_105.empty:
        df_105.loc[:, 'Downtime_Hours'] = df_105['dt_hour'].apply(parse_downtime_duration)
    
    # 101数据集：初始化堆叠图数据结构
    chart_data_101 = {attraction: {cat['name']: 0.0 for cat in categories} for attraction in all_attractions}
    count_data_101 = {attraction: 0 for attraction in all_attractions}
    
    # 填充101数据集的堆叠图数据
    for idx, row in df_101.iterrows():
        original_name = row['Attraction_Name']
        attraction = normalize_attraction_name(original_name)
        category = row['Predicted_Category'] if row['Predicted_Category'] else 'RideMech'
        downtime_hours = row['Downtime_Hours']
        
        if attraction and attraction in chart_data_101 and category in chart_data_101[attraction]:
            chart_data_101[attraction][category] += downtime_hours
            count_data_101[attraction] += 1
    
    # 105数据集：初始化简单柱状图数据结构
    chart_data_105 = {attraction: 0.0 for attraction in all_attractions}
    count_data_105 = {attraction: 0 for attraction in all_attractions}
    
    # 填充105数据集的简单柱状图数据
    for _, row in df_105.iterrows():
        attraction = normalize_attraction_name(row['Attraction_Name'])
        downtime_hours = row['Downtime_Hours']
        
        if attraction and attraction in chart_data_105:
            chart_data_105[attraction] += downtime_hours
            count_data_105[attraction] += 1
    
    # 计算最大值
    max_count_101 = max(count_data_101.values()) if count_data_101.values() else 0
    max_count_105 = max(count_data_105.values()) if count_data_105.values() else 0
    
    y1_max_101 = max_count_101 + 5
    y1_max_105 = max_count_105 + 5
    
    # 计算总停机时长和105发生次数
    total_downtime_hours_101 = sum(sum(chart_data_101[attraction].values()) for attraction in all_attractions)
    total_downtime_hours_105 = sum(chart_data_105.values())
    total_105_occurrence = sum(count_data_105.values())
    
    # 准备JavaScript数据
    attractions_js = '[' + ', '.join([f'"{attr}"' for attr in all_attractions]) + ']'
    
    datasets_101_stacked_js = '[' + ', '.join([
        f'''{{
            label: "{category['label']}",
            data: [{', '.join([str(chart_data_101[attraction][category['name']]) for attraction in all_attractions])}],
            backgroundColor: "{category['color']}"
        }}''' for category in categories
    ]) + ', ' + f'''{{
        label: "Total Count",
        data: [{', '.join([str(count_data_101[attraction]) for attraction in all_attractions])}],
        type: "line",
        borderColor: "rgba(255, 159, 64, 1)",
        backgroundColor: "rgba(255, 159, 64, 0.2)",
        borderWidth: 3,
        fill: false,
        yAxisID: "y1"
    }}''' + ']'
    
    datasets_101_count_js = f'''[{{
        label: "Downtime Count",
        data: [{', '.join([str(count_data_101[attraction]) for attraction in all_attractions])}],
        type: "line",
        borderColor: "rgba(255, 159, 64, 1)",
        backgroundColor: "rgba(255, 159, 64, 0.2)",
        borderWidth: 3,
        fill: false,
        yAxisID: "y1"
    }}]'''
    
    datasets_105_simple_js = f'''[{{
        label: "Downtime Duration (Hours)",
        data: [{', '.join([str(chart_data_105[attraction]) for attraction in all_attractions])}],
        backgroundColor: "rgba(75, 192, 192, 0.7)"
    }}, {{
        label: "Total Count",
        data: [{', '.join([str(count_data_105[attraction]) for attraction in all_attractions])}],
        type: "line",
        borderColor: "rgba(255, 159, 64, 1)",
        backgroundColor: "rgba(255, 159, 64, 0.2)",
        borderWidth: 3,
        fill: false,
        yAxisID: "y1"
    }}]'''
    
    datasets_105_count_js = f'''[{{
        label: "Downtime Count",
        data: [{', '.join([str(count_data_105[attraction]) for attraction in all_attractions])}],
        type: "line",
        borderColor: "rgba(255, 159, 64, 1)",
        backgroundColor: "rgba(255, 159, 64, 0.2)",
        borderWidth: 3,
        fill: false,
        yAxisID: "y1"
    }}]'''
    
    # 生成HTML内容
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Downtime Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-sizing: border-box;
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }}
        .chart-section {{
            margin: 40px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .chart-title {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
        }}
        .chart-container {{
            position: relative;
            height: 700px;
            margin: 30px 0;
        }}
        .info {{
            text-align: center;
            margin: 20px 0;
            color: #666;
            font-size: 16px;
        }}
        .metrics {{
            display: flex;
            justify-content: center;
            gap: 80px;
            margin: 30px 0;
        }}
        .metric {{
            text-align: center;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            font-size: 18px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Weekly Downtime Report</h1>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{mri_value}%</div>
                <div class="metric-label">MRI</div>
            </div>
            <div class="metric">
                <div class="metric-value">{total_downtime_hours_101:.1f}</div>
                <div class="metric-label">Total 101 Downtime (Hours)</div>
            </div>
        </div>
        
        <div class="chart-section">
            <div class="chart-title">101 Data</div>
            <div class="chart-container">
                <canvas id="chart101Stacked"></canvas>
            </div>
        </div>
        
        <div class="chart-section">
            <div class="chart-title">105 Data</div>
            <div class="metrics" style="margin: 20px 0;">
                <div class="metric">
                    <div class="metric-value">{total_105_occurrence}</div>
                    <div class="metric-label">Total 105 Occurrence</div>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="chart105Simple"></canvas>
            </div>
        </div>
    </div>
    
    <script>
        // 注册 datalabels 插件
        Chart.register(ChartDataLabels);
        
        // 101堆叠图
        const ctx101Stacked = document.getElementById('chart101Stacked').getContext('2d');
        new Chart(ctx101Stacked, {{
            type: 'bar',
            data: {{
                labels: {attractions_js},
                datasets: {datasets_101_stacked_js}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        stacked: true,
                        ticks: {{
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45,
                            font: {{
                                size: 11
                            }}
                        }}
                    }},
                    y: {{
                        stacked: true,
                        min: 0,
                        max: 8,
                        title: {{
                            display: true,
                            text: 'Downtime Duration (Hours)'
                        }}
                    }},
                    y1: {{
                        position: 'right',
                        min: 0,
                        max: 8,
                        title: {{
                            display: true,
                            text: 'Count'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'top'
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }},
                    datalabels: {{
                        display: function(context) {{
                            return context.dataset.type === 'line' && context.dataset.data[context.dataIndex] > 0;
                        }},
                        align: 'top',
                        anchor: 'end',
                        font: {{
                            weight: 'bold'
                        }},
                        formatter: function(value) {{
                            return value > 0 ? value : '';
                        }}
                    }}
                }}
            }}
        }});
        
        // 105简单柱状图
        const ctx105Simple = document.getElementById('chart105Simple').getContext('2d');
        new Chart(ctx105Simple, {{
            type: 'bar',
            data: {{
                labels: {attractions_js},
                datasets: {datasets_105_simple_js}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        ticks: {{
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45,
                            font: {{
                                size: 11
                            }}
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Downtime Duration (Hours)'
                        }}
                    }},
                    y1: {{
                        position: 'right',
                        min: 0,
                        max: 8,
                        title: {{
                            display: true,
                            text: 'Count'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        position: 'top'
                    }},
                    datalabels: {{
                        display: function(context) {{
                            return context.dataset.type === 'line' && context.dataset.data[context.dataIndex] > 0;
                        }},
                        align: 'top',
                        anchor: 'end',
                        font: {{
                            weight: 'bold'
                        }},
                        formatter: function(value) {{
                            return value > 0 ? value : '';
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    return html_content


def generate_downtime_report(start_date, end_date):
    """
    生成停机报告的主函数
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    
    返回:
    dict: 包含三个HTML报告内容的字典
    """
    # 从Splunk自动计算MRI值
    mri_value = fetch_mri_from_splunk(start_date, end_date)
    
    # 从Splunk获取数据
    df_101_raw, df_105_raw = fetch_data_from_splunk(start_date, end_date)
    
    # 将Splunk数据转换为期望的格式
    df_101 = process_splunk_data_to_format(df_101_raw, '101')
    df_105 = process_splunk_data_to_format(df_105_raw, '105')
    
    # 使用roberta模型对101数据进行分类
    if not df_101.empty:
        df_101 = classify_downtime_events_with_roberta(df_101)
    
    # 生成Chart HTML报告
    chart_html = generate_downtime_chart_html(df_101, df_105, mri_value)
    
    # 生成详细报告HTML
    detail_html_101, detail_html_105 = generate_downtime_detail_reports(start_date, end_date)
    
    return {
        'chart': chart_html,
        'detail_101': detail_html_101,
        'detail_105': detail_html_105
    }


def generate_downtime_detail_reports(start_date, end_date):
    """
    生成停机详细报告
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    
    返回:
    tuple: (html_101, html_105) 两个详细报告HTML内容
    """
    import sys
    import os
    import re
    from datetime import datetime, timedelta
    from io import StringIO
    import csv
    
    # 导入 downtime_detail_splunk 的函数
    downtime_chart_path = Path(__file__).resolve().parent.parent / 'Downtime_Chart'
    detail_script_path = downtime_chart_path / 'downtime_detail_splunk.py'
    
    # 动态导入模块
    import importlib.util
    spec = importlib.util.spec_from_file_location("downtime_detail_splunk", detail_script_path)
    detail_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detail_module)
    
    # 使用模块中的函数获取数据
    data_101, data_105 = detail_module.fetch_data_from_splunk(start_date, end_date)
    
    # 处理数据
    processed_101 = detail_module.process_data_for_report(data_101, '101')
    processed_105 = detail_module.process_data_for_report(data_105, '105')
    
    # 生成周信息字符串
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    week_info = f"{start_dt.strftime('%m/%d/%Y')} - {end_dt.strftime('%m/%d/%Y')}"
    
    # 生成 HTML 报告
    html_101 = detail_module.generate_html_report(processed_101, '101', week_info)
    html_105 = detail_module.generate_html_report(processed_105, '105', week_info)
    
    return html_101, html_105
