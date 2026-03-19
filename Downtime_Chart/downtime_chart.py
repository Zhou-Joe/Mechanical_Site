import pandas as pd
from predict_downtime_type import DowntimeTypePredictor
from tools_splunk import run_splunk_job

def fetch_data_from_splunk(start_date, end_date):
    """
    从Splunk获取停机数据
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    
    返回:
    tuple: (df_101, df_105) 两个DataFrame，分别对应101和105数据
    """
    print(f"\n从Splunk获取数据: {start_date} 到 {end_date}")
    
    # 构建Splunk查询 - 添加rex字段提取事件类型(101/105)
    spl = f'| artdowntime startdate="{start_date}" enddate="{end_date}" | table _time attractions datetime down_time workorder downtime_summary downtime_details dt_hour mclass fct_downtime_type week_ending | rex field=downtime_summary "(?<type>\\d\\d\\d+)"'
    
    # 执行Splunk查询（不传递earliest/latest，让SPL查询中的artdowntime命令处理日期）
    result = run_splunk_job(spl, max_rows=50000)
    
    if result['status'] != 'success':
        raise Exception(f"Splunk查询失败: {result.get('error', 'Unknown error')}")
    
    # 将结果转换为DataFrame
    rows = result['preview_csv']
    if rows:
        from io import StringIO
        df = pd.read_csv(StringIO(rows))
        print(f"成功获取 {len(df)} 条记录")
        print(f"列名: {df.columns.tolist()}")
        
        # 检查type列是否存在（rex创建的列名是type）
        if 'type' in df.columns:
            print(f"type 唯一值: {df['type'].unique()}")
        if 'fct_downtime_type' in df.columns:
            print(f"fct_downtime_type 唯一值: {df['fct_downtime_type'].unique()}")
            # 只保留 Maintenance 类型的记录
            df_before_filter = df.copy()
            df = df[df['fct_downtime_type'] == 'Maintenance'].copy()
            print(f"筛选 Maintenance 后: {len(df)} 条记录 (过滤掉 {len(df_before_filter) - len(df)} 条)")
        else:
            print("警告: fct_downtime_type 列不存在")
    else:
        df = pd.DataFrame()
        print("没有获取到数据")
    
    # 分离101和105数据
    # 使用type字段来区分101和105数据（rex命令创建的列名是type）
    if not df.empty:
        if 'type' in df.columns:
            # 检查type列的值
            type_values = df['type'].dropna().unique()
            print(f"筛选后type的唯一值: {type_values}")
            
            # 按type分离数据（处理字符串和数字类型）
            # 100和101都是downtime数据，发送到chart 1
            df_101 = df[(df['type'] == '101') | (df['type'] == 101) | (df['type'] == '100') | (df['type'] == 100)].copy()
            df_105 = df[(df['type'] == '105') | (df['type'] == 105)].copy()
            print(f"按type分离: 101/100={len(df_101)}, 105={len(df_105)}")
            
            # 如果101和105都为空，说明所有记录可能是其他类型（如100）
            if len(df_101) == 0 and len(df_105) == 0:
                print("警告: 没有找到101或105类型的记录，将所有Maintenance记录作为101处理")
                df_101 = df.copy()
        else:
            # 如果没有type列，默认全部作为101处理
            df_101 = df.copy()
            df_105 = pd.DataFrame()
            print("警告: type列不存在，将所有数据作为101处理")
    else:
        df_101 = pd.DataFrame()
        df_105 = pd.DataFrame()
    
    print(f"101数据: {len(df_101)} 条记录")
    print(f"105数据: {len(df_105)} 条记录")
    
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
    df_transformed['Maint'] = 'Y'  # 假设都是从Splunk获取的已完成数据
    df_transformed['Report_Date'] = df['datetime'].apply(lambda x: pd.to_datetime(x).strftime('%m/%d/%Y %H:%M') if pd.notna(x) else '')
    df_transformed['Down_Up_Dur'] = df['down_time'].apply(lambda x: str(x) if pd.notna(x) else '')  # Keep as string (datetime)
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
    df_transformed['dt_hour'] = df['dt_hour'].apply(lambda x: float(x) if pd.notna(x) else 0.0)  # 添加dt_hour列
    df_transformed['Code'] = 101 if downtime_type == '101' else 105
    df_transformed['Y_N'] = 'Y'  # 假设都是从Splunk获取的已完成数据
    
    # 提取设施名称中的编号和名称
    # 处理Splunk数据格式：attractions字段直接包含名称，不包含"ID - Name"格式
    def extract_attraction_id(attraction_str):
        """提取设施ID"""
        try:
            # 确保输入是字符串
            if pd.isna(attraction_str):
                return ''
            
            attraction_str = str(attraction_str).strip()
            if attraction_str == '':
                return ''
            
            # 如果包含"Attraction:"前缀且包含" - "分隔符（CSV格式）
            if 'Attraction:' in attraction_str and ' - ' in attraction_str:
                parts = attraction_str.split(' - ', 1)
                if len(parts) == 2:
                    return parts[0].replace('Attraction:', '').strip()
            return ''
        except Exception as e:
            print(f"提取ID时出错: {e}, 原始值: {attraction_str}")
            return ''
    
    def extract_attraction_name(attraction_str):
        """提取设施名称"""
        try:
            # 确保输入是字符串
            if pd.isna(attraction_str):
                return ''
            
            attraction_str = str(attraction_str).strip()
            if attraction_str == '':
                return ''
            
            # 如果包含"Attraction:"前缀
            if 'Attraction:' in attraction_str:
                # 去掉"Attraction:"前缀
                clean_str = attraction_str.replace('Attraction:', '').strip()
                # 如果包含" - "分隔符，取后半部分
                if ' - ' in clean_str:
                    return clean_str.split(' - ', 1)[1].strip()
                # 否则整个字符串就是名称
                return clean_str
            # 否则直接使用字符串
            return attraction_str
        except Exception as e:
            print(f"提取名称时出错: {e}, 原始值: {attraction_str}")
            return ''
    
    # 提取ID和Name
    df_transformed['Attraction_ID'] = df_transformed['Attraction'].apply(extract_attraction_id)
    df_transformed['Attraction_Name'] = df_transformed['Attraction'].apply(extract_attraction_name)
    
    # 调试：打印前5行的Attraction信息
    print("\n调试验证 - 前5行的Attraction信息:")
    for idx in range(min(5, len(df_transformed))):
        print(f"  Row {idx}: Attraction='{df_transformed.iloc[idx]['Attraction']}', ID='{df_transformed.iloc[idx]['Attraction_ID']}', Name='{df_transformed.iloc[idx]['Attraction_Name']}'")
    
    # 对于 Soaring 的设施，格式化为 "Soaring Over the Horizon (Ride A)" 或 "Soaring Over the Horizon (Ride B)"
    def format_attraction_name(row):
        attraction_id = row['Attraction_ID'] if pd.notna(row['Attraction_ID']) else ''
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) else ''
        
        # 只有 Soaring 的设施需要添加括号编号
        if 'Soaring' in attraction_name and attraction_id in ['Ride A', 'Ride B']:
            return f"{attraction_name} ({attraction_id})"
        else:
            return attraction_name
    
    df_transformed['Attraction_Name'] = df_transformed.apply(format_attraction_name, axis=1)
    
    # 转换Code列为整数
    df_transformed['Code'] = df_transformed['Code'].astype('Int64')
    
    return df_transformed

def read_and_process_csv(file_path='101.csv'):
    # 定义列名（包含Park列和Root Cause Details列，用于101.csv的新版本）
    columns_with_park_22 = [
        "Park", 
        "Attraction", 
        "Root_Cause_Problem_Cause_Remedy", 
        "Reason_Code_Split", 
        "Root_Cause_Details", 
        "Down_Code", 
        "Maint", 
        "Classification", 
        "Report_Date", 
        "Down_Up_Dur", 
        "Work_Order", 
        "Reason_Code", 
        "Operations", 
        "Category", 
        "Date_Time", 
        "Time_Range", 
        "Work_Order_Details", 
        "Reason_Details", 
        "Unnamed", 
        "Classification_Details", 
        "Code", 
        "Y_N"
    ]
    
    # 定义列名（包含Park列，用于101.csv的旧版本）
    columns_with_park = [
        "Park", 
        "Attraction", 
        "Root_Cause_Problem_Cause_Remedy", 
        "Down_Code", 
        "Maint", 
        "Classification", 
        "Report_Date", 
        "Down_Up_Dur", 
        "Work_Order", 
        "Reason_Code", 
        "Operations", 
        "Category", 
        "Date_Time", 
        "Time_Range", 
        "Work_Order_Details", 
        "Reason_Details", 
        "Unnamed", 
        "Classification_Details", 
        "Code", 
        "Y_N"
    ]
    
    # 定义列名（不包含Park列，用于105.csv）
    columns_without_park = [
        "Attraction", 
        "Root_Cause_Problem_Cause_Remedy", 
        "Down_Code", 
        "Maint", 
        "Classification", 
        "Report_Date", 
        "Down_Up_Dur", 
        "Work_Order", 
        "Reason_Code", 
        "Operations", 
        "Category", 
        "Date_Time", 
        "Time_Range", 
        "Work_Order_Details", 
        "Reason_Details", 
        "Unnamed", 
        "Classification_Details", 
        "Code", 
        "Y_N"
    ]

    # 读取数据
    # 对于101.csv，需要跳过第一行标题
    # 对于105.csv，直接读取（没有标题行）
    if '101' in file_path:
        df = pd.read_csv(file_path, skiprows=1, header=None, on_bad_lines='skip')
    else:
        df = pd.read_csv(file_path, header=None, on_bad_lines='skip')

    # 根据实际列数选择合适的列名列表
    if len(df.columns) == 22:
        df.columns = columns_with_park_22
    elif len(df.columns) == 20:
        df.columns = columns_with_park
    elif len(df.columns) == 19:
        df.columns = columns_without_park
    else:
        raise ValueError(f"CSV文件 {file_path} 的列数 {len(df.columns)} 不符合预期（应为19、20或22列）")

    # 删除最后一行（页脚信息）- 仅当有多于一行数据时才删除
    if len(df) > 1:
        df = df.drop(df.index[-1])

    # 数据清洗
    # 提取设施名称中的编号和名称（支持数字编号和字母编号，如 "302 - Tron" 或 "Ride A - Soaring"）
    df['Attraction_ID'] = df['Attraction'].str.extract(r'Attraction: (.+?) - (.*)')[0]
    df['Attraction_Name'] = df['Attraction'].str.extract(r'Attraction: (.+?) - (.*)')[1]
    
    # 对于 Soaring 的设施，格式化为 "Soaring Over the Horizon (Ride A)" 或 "Soaring Over the Horizon (Ride B)"
    # 其他设施保持原名称，不添加括号编号
    def format_attraction_name(row):
        attraction_id = row['Attraction_ID'] if pd.notna(row['Attraction_ID']) else ''
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) else ''
        
        # 只有 Soaring 的设施需要添加括号编号
        if 'Soaring' in attraction_name and attraction_id in ['Ride A', 'Ride B']:
            return f"{attraction_name} ({attraction_id})"
        else:
            return attraction_name
    
    df['Attraction_Name'] = df.apply(format_attraction_name, axis=1)

    # 提取分类详情的主要类别
    df['Main_Category'] = df['Classification_Details'].str.extract(r'(\d+ - [^-]+)')

    # 转换Code列为整数
    df['Code'] = df['Code'].astype('Int64')
    
    return df

def filter_completed_repairs(df):
    """
    筛选出已完成(Y)的维修记录
    
    参数:
    df (pandas.DataFrame): 原始DataFrame
    
    返回:
    pandas.DataFrame: 筛选后的DataFrame
    """
    if df.empty:
        return df
    return df[df['Y_N'] == 'Y']

# 全局变量存储预测器实例
_predictor = None

def classify_downtime_events_with_roberta(df):
    """
    使用roberta模型对停机事件进行分类
    
    参数:
    df (pandas.DataFrame): 包含停机事件的DataFrame
    
    返回:
    pandas.DataFrame: 添加了分类结果的DataFrame
    """
    global _predictor
    
    # 初始化roberta预测器（仅在第一次调用时初始化）
    if _predictor is None:
        _predictor = DowntimeTypePredictor()
    
    # 添加分类结果列
    df = df.copy()
    df.loc[:, 'Predicted_Category'] = ""
    
    # 对每个事件进行分类
    for idx, row in df.iterrows():
        # 获取设施名称和分类详情文本
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) else ''
        classification_details = row['Classification_Details'] if pd.notna(row['Classification_Details']) else ''
        category = row['Category'] if pd.notna(row['Category']) else ''
        
        # 组合文本用于预测
        description = f"{classification_details} {category}"
        
        # 使用roberta模型进行预测
        try:
            result = _predictor.predict(attraction_name, description)
            predicted_category = result['predicted_class']
        except Exception as e:
            print(f"预测失败，使用默认分类: {e}")
            # 如果预测失败，则使用默认分类
            # 检查是否与游乐设施相关
            ride_related_keywords = ['ride', 'attraction', 'vehicle', 'track', 'train']
            show_related_keywords = ['show', 'performance', 'theater', 'stage']
            
            is_ride_related = any(keyword in (attraction_name + ' ' + category).lower() for keyword in ride_related_keywords)
            is_show_related = any(keyword in (attraction_name + ' ' + category).lower() for keyword in show_related_keywords)
            
            if is_ride_related:
                predicted_category = 'RideMech'  # 默认为RideMech
            elif is_show_related:
                predicted_category = 'ShowMech'  # 默认为ShowMech
            else:
                predicted_category = 'Facility'  # 默认为Facility
        
        # 将结果保存到DataFrame
        df.loc[idx, 'Predicted_Category'] = predicted_category
    
    return df

def display_dataframe_info(df, title="DataFrame"):
    """
    显示DataFrame信息
    
    参数:
    df (pandas.DataFrame): 要显示的DataFrame
    title (str): 标题
    """
    pass

def display_classification_results(df):
    """
    显示分类结果统计信息
    
    参数:
    df (pandas.DataFrame): 包含分类结果的DataFrame
    """
    pass
    

def generate_comprehensive_chart_html(df_101, df_105, mri_value, output_file='downtime_comprehensive_chart.html'):
    """
    生成综合图表HTML文件，包含101和105两个数据集的图表
    
    参数:
    df_101 (pandas.DataFrame): 101数据集的DataFrame（包含分类结果）
    df_105 (pandas.DataFrame): 105数据集的DataFrame（不包含分类结果）
    output_file (str): 输出HTML文件名
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
    
    # 创建名称映射表：将Splunk返回的名称映射到标准名称
    attraction_name_mapping = {
        # Actual names from Splunk (from attrname_in_splunk.csv)
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
        
        # Additional variations for robustness
        'El Teatro Fandango': 'El Teatro Fandango',
        'Tron Realm Chevrolet Challenge': 'Tron Realm Chevrolet Challenge',
        'Pirates of the Caribbean - Battle for the Sunken Treasure': 'Pirates of Caribbean: Battle for the Sunken Treasure',
        'Dumbo the Flying Elephant': 'Dumbo The Flying Elephant',
        'Battle for the Sunken Treasure': 'Pirates of Caribbean: Battle for the Sunken Treasure',
        'Soaring Over Horizon (Ride A)': 'Soaring Over the Horizon (Ride A)',
        'Soaring Over Horizon (Ride B)': 'Soaring Over the Horizon (Ride B)',
    }
    
    # 标准化设施名称的函数
    def normalize_attraction_name(name):
        """将设施名称标准化为图表中使用的名称"""
        if pd.isna(name) or name == '':
            return None
        
        # 去除首尾空格
        name = str(name).strip()
        
        # 首先尝试直接匹配映射表
        if name in attraction_name_mapping:
            return attraction_name_mapping[name]
        
        # 如果不在映射表中，尝试模糊匹配（去除空格、大小写等）
        normalized = name.lower().replace('-', ' ').replace('_', ' ')
        
        # 遍历映射表，查找模糊匹配
        for splunk_name, standard_name in attraction_name_mapping.items():
            splunk_normalized = splunk_name.lower().replace('-', ' ').replace('_', ' ')
            if normalized == splunk_normalized:
                return standard_name
        
        # 如果仍然没有匹配，返回原名称（警告会在后面处理）
        return name
    
    # 定义停机类别和颜色（用于101数据集的堆叠图）
    categories = [
        {'name': 'RideMech', 'label': 'Ride Mechanical', 'color': 'rgba(255, 0, 0, 0.7)'},
        {'name': 'RideControl', 'label': 'Ride Control', 'color': 'rgba(0, 255, 0, 0.7)'},
        {'name': 'ShowMech', 'label': 'Show Mechanical', 'color': 'rgba(0, 0, 255, 0.7)'},
        {'name': 'ShowControl', 'label': 'Show Control', 'color': 'rgba(255, 105, 203, 0.7)'},
        {'name': 'Facility', 'label': 'Facility', 'color': 'rgba(153, 102, 255, 0.7)'}
    ]
    
    # 解析停机时长（直接使用dt_hour列）
    def parse_downtime_duration(dt_hour):
        """从dt_hour列提取停机时长（小时）"""
        try:
            if pd.isna(dt_hour) or dt_hour == '':
                return 0.0
            
            # dt_hour已经是小时数，直接返回
            return float(dt_hour)
        except:
            return 0.0
    
    # 为DataFrame添加停机时长列（处理空DataFrame的情况）
    if not df_101.empty:
        df_101.loc[:, 'Downtime_Hours'] = df_101['dt_hour'].apply(parse_downtime_duration)
    if not df_105.empty:
        df_105.loc[:, 'Downtime_Hours'] = df_105['dt_hour'].apply(parse_downtime_duration)
    
    # 101数据集：初始化堆叠图数据结构
    chart_data_101 = {attraction: {cat['name']: 0.0 for cat in categories} for attraction in all_attractions}
    count_data_101 = {attraction: 0 for attraction in all_attractions}
    
    # 填充101数据集的堆叠图数据
    
    print("\n开始填充101数据集...")
    unmatched_count = 0
    for idx, row in df_101.iterrows():
        
        # 标准化设施名称
        original_name = row['Attraction_Name']
        attraction = normalize_attraction_name(original_name)
        # 使用已有的分类结果，如果没有则使用默认分类
        category = row['Predicted_Category'] if row['Predicted_Category'] else 'RideMech'
        downtime_hours = row['Downtime_Hours']
        
        # Debug: 打印前5条的转换情况
        if idx < 5:
            print(f"  Record {idx}: Original='{original_name}', Normalized='{attraction}', In list={attraction in chart_data_101}")
        
        # 只处理有效的景点和类别
        if attraction and attraction in chart_data_101 and category in chart_data_101[attraction]:
            chart_data_101[attraction][category] += downtime_hours
            count_data_101[attraction] += 1
        else:
            if attraction:
                unmatched_count += 1
                if unmatched_count <= 5:
                    print(f"    ⚠️ Not matched: Attraction='{attraction}', Category='{category}'")
    
    print(f"  总记录数: {len(df_101)}, 不匹配记录数: {unmatched_count}")
    print(f"  匹配的景点数量: {sum(1 for v in count_data_101.values() if v > 0)}")
    
    # 105数据集：初始化简单柱状图数据结构
    chart_data_105 = {attraction: 0.0 for attraction in all_attractions}
    count_data_105 = {attraction: 0.0 for attraction in all_attractions}

    
    # 填充105数据集的简单柱状图数据
    for _, row in df_105.iterrows():
        # 标准化设施名称
        attraction = normalize_attraction_name(row['Attraction_Name'])
        downtime_hours = row['Downtime_Hours']
        
        # 只处理有效的景点
        if attraction and attraction in chart_data_105:
            chart_data_105[attraction] += downtime_hours
            count_data_105[attraction] += 1
    
    # 计算101和105数据集的计数最大值，用于设置Y轴最大值
    max_count_101 = max(count_data_101.values()) if count_data_101.values() else 0
    max_count_105 = max(count_data_105.values()) if count_data_105.values() else 0
    total_count_105 = sum(count_data_105.values())
    #print (total_count_105)

    
    # 设置Y轴最大值为当前最大值+5
    y1_max_101 = max_count_101 + 5
    y1_max_105 = max_count_105 + 5
    
    # 准备Chart.js数据
    attractions_js = '[' + ', '.join([f'"{attr}"' for attr in all_attractions]) + ']'
    
    # 101数据集的堆叠图数据
    datasets_101_stacked = []
    for category in categories:
        cat_name = category['name']
        data = [chart_data_101[attraction][cat_name] for attraction in all_attractions]
        datasets_101_stacked.append({
            'label': category['label'],
            'data': data,
            'backgroundColor': category['color']
        })
    
    # 101数据集的计数线图数据
    count_data_101_list = [count_data_101[attraction] for attraction in all_attractions]
    datasets_101_count = [{
        'label': 'Downtime Count',
        'data': count_data_101_list,
        'type': 'line',
        'borderColor': 'rgba(255, 159, 64, 1)',
        'backgroundColor': 'rgba(255, 159, 64, 0.2)',
        'borderWidth': 3,
        'fill': False,
        'yAxisID': 'y1'
    }]
    
    # 105数据集的简单柱状图数据
    duration_data_105_list = [chart_data_105[attraction] for attraction in all_attractions]
    datasets_105_simple = [{
        'label': 'Downtime Duration (Hours)',
        'data': duration_data_105_list,
        'backgroundColor': 'rgba(75, 192, 192, 0.7)'
    }]
    
    # 105数据集的计数线图数据
    count_data_105_list = [count_data_105[attraction] for attraction in all_attractions]
    datasets_105_count = [{
        'label': 'Downtime Count',
        'data': count_data_105_list,
        'type': 'line',
        'borderColor': 'rgba(255, 159, 64, 1)',
        'backgroundColor': 'rgba(255, 159, 64, 0.2)',
        'borderWidth': 3,
        'fill': False,
        'yAxisID': 'y1'
    }]
    
    # 将数据转换为JavaScript格式
    datasets_101_stacked_js = '[' + ', '.join([
        f'''{{
            label: "{category['label']}",
            data: [{', '.join([str(chart_data_101[attraction][category['name']]) for attraction in all_attractions])}],
            backgroundColor: "{category['color']}"
        }}''' for category in categories
    ]) + ']'
    
    datasets_101_count_js = f'''[{{label: "Downtime Count", data: [{', '.join([str(count_data_101[attraction]) for attraction in all_attractions])}], type: "line", borderColor: "rgba(255, 159, 64, 1)", backgroundColor: "rgba(255, 159, 64, 0.2)", borderWidth: 3, fill: false, yAxisID: "y1"}}]'''
    
    datasets_105_simple_js = f'''[{{label: "Downtime Duration (Hours)", data: [{', '.join([str(chart_data_105[attraction]) for attraction in all_attractions])}], backgroundColor: "rgba(75, 192, 192, 0.7)"}}]'''
    
    datasets_105_count_js = f'''[{{label: "Downtime Count", data: [{', '.join([str(count_data_105[attraction]) for attraction in all_attractions])}], type: "line", borderColor: "rgba(255, 159, 64, 1)", backgroundColor: "rgba(255, 159, 64, 0.2)", borderWidth: 3, fill: false, yAxisID: "y1"}}]'''
    
    # Calculate total downtime hours for 101 dataset
    total_downtime_hours_101 = sum(sum(chart_data_101[attraction].values()) for attraction in all_attractions)
  


    
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
            margin-top: 10px;
        }}
        .input-field {{
            width: 100px;
            padding: 8px;
            font-size: 18px;
            text-align: center;
            border: 2px solid #ddd;
            border-radius: 6px;
            margin-top: 5px;
        }}
        .mri-display {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
            min-height: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Weekly Downtime Report</h1>
        
        <!-- 101数据集图表 -->
        <div class="chart-section">
            <h2 class="chart-title">Downtime Data</h2>
            <!-- Metrics section -->
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" id="totalDowntimeHours">{total_downtime_hours_101:.1f}</div>
                    <div class="metric-label">Total Downtime Hours</div>
                </div>
                <div class="metric">
                    <div class="mri-display" id="mriDisplay">{mri_value}%</div>
                    <div class="metric-label">MRI (%)</div>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="downtimeChart101"></canvas>
            </div>
        </div>
        
        <!-- 105数据集图表 -->
        <div class="chart-section">
            <h2 class="chart-title">105 Data</h2>
                        <div class="metrics">
                <div class="metric">
                    <div class="metric-value" id="totalDowntimeHours">{total_count_105:.0f}</div>
                    <div class="metric-label">Total 105 Count</div>
                </div>

            </div>
            <div class="chart-container">
                <canvas id="downtimeChart105"></canvas>
            </div>
        </div>
    </div>

    <script>
        // Register the datalabels plugin
        Chart.register(ChartDataLabels);
        
        // Chart data
        const attractions = {attractions_js};
        
        // 101数据集图表
        const ctx101 = document.getElementById('downtimeChart101').getContext('2d');
        const chart101 = new Chart(ctx101, {{
            type: 'bar',
            data: {{
                labels: attractions,
                datasets: [...{datasets_101_stacked_js}, ...{datasets_101_count_js}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Attractions'
                        }},
                        stacked: true,
                        ticks: {{
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Downtime Hours'
                        }},
                        stacked: true,
                        max: 8
                    }},
                    y1: {{
                        beginAtZero: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Downtime Count'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }},
                        max: {y1_max_101}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{
                            padding: 50
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }},
                    datalabels: {{
                        anchor: 'end',
                        align: 'top',
                        formatter: (value, context) => {{
                            // Only display labels for non-zero values
                            if (value <= 0) return '';
                            
                            // Check if this is a count dataset (line chart)
                            if (context.dataset.label === 'Downtime Count') {{
                                // For count datasets, show as integer
                                return value.toFixed(0);
                            }} else {{
                                // For duration datasets, show with 1 decimal place
                                return '';
                            }}
                        }},
                        font: {{
                            weight: 'bold',
                            size: 10
                        }},
                        color: '#333'
                    }}
                }}
            }}
        }});
        
        // 105数据集图表
        const ctx105 = document.getElementById('downtimeChart105').getContext('2d');
        const chart105 = new Chart(ctx105, {{
            type: 'bar',
            data: {{
                labels: attractions,
                datasets: [...{datasets_105_simple_js}, ...{datasets_105_count_js}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Attractions'
                        }},
                        ticks: {{
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 45
                        }}
                    }},
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Downtime Hours'
                        }}
                    }},
                    y1: {{
                        beginAtZero: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Downtime Count'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }},
                        max: {y1_max_105}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{
                            padding: 40
                        }}
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }},
                    datalabels: {{
                        anchor: 'end',
                        align: 'top',
                        formatter: (value, context) => {{
                            // Only display labels for non-zero values
                            if (value <= 0) return '';
                            
                            // Check if this is a count dataset (line chart)
                            if (context.dataset.label === 'Downtime Count') {{
                                // For count datasets, show as integer
                                return value.toFixed(0);
                            }} else {{
                                // For duration datasets, show with 1 decimal place
                                return value.toFixed(1);
                            }}
                        }},
                        font: {{
                            weight: 'bold',
                            size: 10
                        }},
                        color: '#333'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

def manual_classification_review(df):
    """
    人工审核分类结果
    
    参数:
    df (pandas.DataFrame): 包含自动分类结果的DataFrame
    
    返回:
    pandas.DataFrame: 更新后的DataFrame
    """
    # 定义分类类别
    categories = {
        1: "RideMech",
        2: "RideControl",
        3: "ShowMech",
        4: "ShowControl",
        5: "Facility"
    }
    
    print("\n开始人工审核分类结果...")
    print("分类选项:")
    for num, category in categories.items():
        print(f"{num}. {category}")
    print("如果分类正确，请直接按回车键确认。如果需要修改，请输入对应的数字。\n")
    
    # 遍历每一行数据
    for idx, row in df.iterrows():
        # 显示当前记录的信息
        attraction_name = row['Attraction_Name'] if pd.notna(row['Attraction_Name']) and row['Attraction_Name'].strip() != '' else 'N/A'
        classification_details = row['Classification_Details'] if pd.notna(row['Classification_Details']) and row['Classification_Details'].strip() != '' else 'N/A'
        predicted_category = row['Predicted_Category'] if pd.notna(row['Predicted_Category']) and row['Predicted_Category'].strip() != '' else 'N/A'
        
        print(f"记录 {idx+1}/{len(df)}:")
        print(f"  设施名称: {attraction_name}")
        print(f"  分类详情: {classification_details}")
        print(f"  自动分类: {predicted_category}")
        
        # 获取用户输入
        while True:
            try:
                user_input = input("请输入分类编号 (1=RideMech, 2=RideControl, 3=ShowMech, 4=ShowControl, 5=Facility) 或直接按回车确认: ").strip()
            except EOFError:
                # 如果遇到 EOFError（非交互式环境），自动确认当前分类
                print("  检测到非交互式环境，自动确认所有分类。\n")
                return df
            
            # 如果用户直接按回车，表示确认当前分类
            if user_input == "":
                print("  分类已确认，保持不变。\n")
                break
            
            # 如果用户输入数字，检查是否有效并更新分类
            try:
                category_num = int(user_input)
                if category_num in categories:
                    df.loc[idx, 'Predicted_Category'] = categories[category_num]
                    print(f"  分类已更新为: {categories[category_num]}\n")
                    break
                else:
                    print("  无效的输入，请输入1-5之间的数字或直接按回车确认。")
            except ValueError:
                print("  无效的输入，请输入1-5之间的数字或直接按回车确认。")
    
    print("人工审核完成！\n")
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
    import time as time_module
    import datetime as dt_module
    
    print(f"\n从Splunk计算MRI值: {start_date} 到 {end_date}")
    
    # 将日期转换为Unix epoch时间戳
    start_dt = dt_module.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = dt_module.datetime.strptime(end_date, "%Y-%m-%d")
    
    # 转换为epoch时间戳（秒）
    start_epoch = str(int(start_dt.timestamp()))
    end_epoch = str(int(end_dt.timestamp() + 86399))  # +86399秒 = 23:59:59
    
    # 构建Splunk查询 - 使用提供的MRI计算查询
    # 注意：使用Unix epoch时间戳作为earliest/latest参数
    # 因此不需要传递earliest/latest参数给run_splunk_job
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
    
    # 执行Splunk查询 - 不传递earliest/latest参数，因为查询中已经包含了时间约束
    result = run_splunk_job(spl)
    
    if result['status'] != 'success':
        raise Exception(f"Splunk MRI查询失败: {result.get('error', 'Unknown error')}")
    
    # 将结果转换为DataFrame
    rows = result['preview_csv']
    if rows:
        from io import StringIO
        df = pd.read_csv(StringIO(rows))
        if not df.empty and 'mri' in df.columns:
            # 获取最新的MRI值（第一条记录，因为按week_ending desc排序）
            mri_value = df.iloc[0]['mri']
            print(f"成功获取MRI值: {mri_value}%")
            return float(mri_value)
        else:
            print("警告: 没有找到MRI数据，使用默认值95.0")
            return 95.0
    else:
        print("警告: 没有获取到MRI数据，使用默认值95.0")
        return 95.0

def main(start_date, end_date):
    """
    主函数
    
    参数:
    start_date (str): 开始日期，格式 "YYYY-MM-DD"
    end_date (str): 结束日期，格式 "YYYY-MM-DD"
    """
    # 从Splunk自动计算MRI值
    mri_value = fetch_mri_from_splunk(start_date, end_date)
    
    # 从Splunk获取数据
    df_101_raw, df_105_raw = fetch_data_from_splunk(start_date, end_date)
    
    # 将Splunk数据转换为期望的格式
    df_101 = process_splunk_data_to_format(df_101_raw, '101')
    df_105 = process_splunk_data_to_format(df_105_raw, '105')
    
    # 筛选已完成的维修记录（从Splunk获取的数据默认已完成，但仍需要筛选）
    df_101_completed = filter_completed_repairs(df_101).copy()
    df_105_completed = filter_completed_repairs(df_105).copy()
    
    # Add predicted category column to DataFrame (if it doesn't exist)
    if 'Predicted_Category' not in df_101_completed.columns:
        df_101_completed['Predicted_Category'] = ''
    
    # 使用roberta模型对筛选后的数据进行分类
    df_101_classified = classify_downtime_events_with_roberta(df_101_completed)
    
    # 人工审核分类结果
    df_101_reviewed = manual_classification_review(df_101_classified)
    
    # 保存分类结果到新文件
    df_101_reviewed.to_csv('downtime_classification_results_101.csv', index=False)
    
    # 生成综合图表HTML文件
    generate_comprehensive_chart_html(df_101_reviewed, df_105_completed, mri_value, 'downtime_comprehensive_chart.html')
    
    # 保存筛选后的数据到新文件
    df_101_completed.to_csv('completed_repairs_101.csv', index=False)
    df_105_completed.to_csv('completed_repairs_105.csv', index=False)


if __name__ == "__main__":
    # 输入日期范围
    start_date = input("Input start date (YYYY-MM-DD):\t")
    end_date = input("Input end date (YYYY-MM-DD):\t")
    
    # 运行主函数（MRI值将自动从Splunk计算）
    main(start_date, end_date)
