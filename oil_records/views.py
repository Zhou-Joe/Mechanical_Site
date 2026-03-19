from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.urls import reverse
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import queue
import threading
from django.conf import settings
from .models import Attraction, Equipment, OilInspectionReport, OilParameter, UploadedFile

# 全局任务状态存储
batch_upload_tasks = {}
batch_upload_results = {}

def me_home(request):
    """Mechanical Engineering 系统首页"""
    # 获取统计数据
    oil_report_count = OilInspectionReport.objects.count()
    equipment_count = Equipment.objects.count()
    attraction_count = Attraction.objects.count()
    
    # 获取正常和异常报告数量
    normal_count = OilInspectionReport.objects.filter(
        oilparameter__is_normal=True
    ).distinct().count()
    warning_count = OilInspectionReport.objects.filter(
        oilparameter__is_normal=False
    ).distinct().count()
    
    # 计算百分比
    total_params = OilParameter.objects.count()
    normal_params = OilParameter.objects.filter(is_normal=True).count()
    normal_percentage = round((normal_params / total_params * 100), 1) if total_params > 0 else 0
    
    context = {
        'oil_report_count': oil_report_count,
        'equipment_count': equipment_count,
        'attraction_count': attraction_count,
        'normal_count': normal_count,
        'warning_count': warning_count,
        'normal_percentage': normal_percentage,
    }
    return render(request, 'oil_records/me_home.html', context)

def dashboard(request):
    """油品检测仪表板（Oil Inspection子模块）"""
    attractions = Attraction.objects.all().order_by('name')
    context = {
        'attractions': attractions,
    }
    return render(request, 'oil_records/dashboard.html', context)

def upload_report(request):
    """上传油品报告（手动模式）"""
    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            
            # 保存上传的文件记录
            uploaded_file = UploadedFile.objects.create(
                file=pdf_file,
                original_filename=pdf_file.name,
                file_type='pdf',
                file_size=pdf_file.size,
                processing_status='pending'
            )
            
            try:
                # 调用mineru-api进行OCR处理
                print(f"开始处理文件: {pdf_file.name}")
                md_content = call_mineru_api(pdf_file)
                print(f"OCR处理完成，MD内容长度: {len(md_content)}")
                
                # 处理OCR结果并保存到数据库
                process_ocr_result(uploaded_file, md_content, request.POST, pdf_file.name)
                print("数据保存完成")
                
                # 获取刚创建的报告来统计参数数量
                report = OilInspectionReport.objects.filter(pdf_file=uploaded_file.file).order_by('-created_at').first()
                param_count = OilParameter.objects.filter(report=report).count() if report else 0
                messages.success(request, f'油品报告上传并处理成功！解析了{param_count}个参数。')
                return redirect('oil_records:dashboard')
                
            except Exception as e:
                print(f"处理失败: {e}")
                uploaded_file.processing_status = 'failed'
                uploaded_file.error_message = str(e)
                uploaded_file.save()
                messages.error(request, f'处理失败：{str(e)}')
        else:
            messages.error(request, '请选择要上传的PDF文件')
    
    # GET请求时传递attractions数据
    attractions = Attraction.objects.all().order_by('name')
    context = {
        'attractions': attractions,
    }
    return render(request, 'oil_records/upload.html', context)

def upload_report_simple(request):
    """智能上传油品报告（自动模式）"""
    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            
            # 检查是否是OCR预览请求
            if request.POST.get('action') == 'ocr_preview':
                return ocr_preview_data(request, pdf_file)
            
            # 检查是否是预览请求
            if request.POST.get('action') == 'preview':
                return preview_upload_data(request, pdf_file)
            
            # 检查是否是确认导入请求
            elif request.POST.get('action') == 'confirm':
                return confirm_upload_data(request)
            
            # 默认行为：跳转到OCR预览
            else:
                return ocr_preview_data(request, pdf_file)
        else:
            messages.error(request, '请选择要上传的PDF文件')
    
    # GET请求时显示简化上传页面
    attractions = Attraction.objects.all().order_by('name')
    return render(request, 'oil_records/upload_simple.html', {'attractions': attractions})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def batch_upload(request):
    """批量上传PDF文件并自动处理到数据库"""
    if request.method == 'POST':
        if 'pdf_files' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': '请选择要上传的PDF文件'
            })

        pdf_files = request.FILES.getlist('pdf_files')
        if not pdf_files:
            return JsonResponse({
                'success': False,
                'error': '没有有效的PDF文件'
            })

        # 获取批量上传选项
        auto_upload = request.POST.get('auto_upload') == 'true'
        skip_duplicates = request.POST.get('skip_duplicates') == 'true'
        continue_on_error = request.POST.get('continue_on_error') == 'true'
        upload_non_duplicate_only = request.POST.get('upload_non_duplicate_only') == 'true'

        print(f"开始批量处理 {len(pdf_files)} 个文件")
        print(f"选项: 自动上传={auto_upload}, 跳过重复={skip_duplicates}, 错误时继续={continue_on_error}, 仅上传不重复日期={upload_non_duplicate_only}")

        results = []
        processed_count = 0
        success_count = 0
        skipped_count = 0
        error_count = 0

        # 导入智能提取函数
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        try:
            from smart_equipment_extraction import extract_equipment_info_complete, find_or_create_equipment
            from enhanced_multi_measurement_extraction import extract_multi_measurement_data_enhanced, create_multiple_reports_enhanced
        except ImportError as e:
            print(f"导入智能提取函数失败: {e}")
            return JsonResponse({
                'success': False,
                'error': f'智能提取功能不可用: {str(e)}'
            })

        for i, pdf_file in enumerate(pdf_files):
            file_result = {
                'filename': pdf_file.name,
                'status': 'pending',
                'message': '',
                'equipment_name': '',
                'report_count': 0,
                'error': ''
            }

            try:
                print(f"\n处理文件 {i+1}/{len(pdf_files)}: {pdf_file.name}")

                # 检查文件大小
                if pdf_file.size > 50 * 1024 * 1024:  # 50MB限制
                    raise ValueError(f"文件太大: {pdf_file.size / 1024 / 1024:.1f}MB，请使用小于50MB的文件")

                # OCR处理
                print(f"开始OCR处理: {pdf_file.name}")
                pdf_file.seek(0)  # 重置文件指针
                md_content = call_mineru_api(pdf_file)
                print(f"OCR处理完成，MD内容长度: {len(md_content)}")

                # 智能提取设备信息
                equipment_info = extract_equipment_info_complete(md_content, pdf_file.name)
                # 添加文件名到设备信息中，用于匹配
                equipment_info['filename'] = pdf_file.name
                equipment, created = find_or_create_equipment(equipment_info)

                file_result['equipment_name'] = equipment.name
                if created:
                    print(f"创建新设备: {equipment.name}")
                else:
                    print(f"使用现有设备: {equipment.name}")

                # 生成报告编号
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_number_base = f"BATCH_{timestamp}_{i+1}"

                # 保存上传文件记录
                uploaded_file = UploadedFile.objects.create(
                    file=pdf_file,
                    original_filename=pdf_file.name,
                    file_type='pdf',
                    file_size=pdf_file.size,
                    processing_status='processing'
                )

                # 尝试提取多次测量数据
                multi_data = extract_multi_measurement_data_enhanced(md_content)
                has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1

                # 检查重复文件（优先检查设备和日期组合）
                duplicate_dates = []
                new_dates = []
                
                if has_multiple_measurements and multi_data['sample_dates']:
                    # 检查哪些日期已存在，哪些日期是新的
                    from datetime import datetime
                    sample_dates = []
                    for date_str in multi_data['sample_dates']:
                        if isinstance(date_str, str):
                            try:
                                sample_dates.append(datetime.strptime(date_str, '%Y-%m-%d').date())
                            except ValueError:
                                try:
                                    sample_dates.append(datetime.fromisoformat(date_str.replace('Z', '+00:00')).date())
                                except ValueError:
                                    print(f"无法解析日期: {date_str}")
                                    continue
                        else:
                            sample_dates.append(date_str)
                    
                    existing_reports = OilInspectionReport.objects.filter(
                        equipment=equipment,
                        sample_date__in=sample_dates
                    ).values_list('sample_date', flat=True)
                    
                    existing_dates_set = set(existing_reports)
                    new_dates = [date for date in sample_dates if date not in existing_dates_set]
                    duplicate_dates = [date for date in sample_dates if date in existing_dates_set]
                else:
                    # 对于单次测量，从equipment_info获取日期
                    sample_date = equipment_info.get('sample_date') or equipment_info.get('report_date')
                    if sample_date:
                        if isinstance(sample_date, str):
                            from datetime import datetime
                            try:
                                sample_date = datetime.strptime(sample_date, '%Y-%m-%d').date()
                            except ValueError:
                                pass
                        
                        existing_report = OilInspectionReport.objects.filter(
                            equipment=equipment,
                            sample_date=sample_date
                        ).first()
                        
                        if existing_report:
                            duplicate_dates = [sample_date]
                        else:
                            new_dates = [sample_date]

                # 根据选项决定如何处理重复
                if skip_duplicates and not upload_non_duplicate_only:
                    # 传统模式：如果存在任何重复，跳过整个文件
                    if duplicate_dates:
                        file_result['status'] = 'skipped'
                        file_result['message'] = f'跳过重复文件（设备已有{duplicate_dates[0]}等日期的报告）'
                        file_result['equipment_name'] = equipment.name
                        skipped_count += 1
                        results.append(file_result)
                        print(f"跳过重复文件: {pdf_file.name} - 设备{equipment.name}在{duplicate_dates}已有报告")
                        continue
                
                # 检查报告编号重复（仅在非"仅上传不重复日期"模式下）
                if not upload_non_duplicate_only:
                    existing_reports = OilInspectionReport.objects.filter(
                        equipment=equipment,
                        report_number__startswith=report_number_base.split('_')[0] + '_' + report_number_base.split('_')[1]
                    )
                    if existing_reports.exists():
                        file_result['status'] = 'skipped'
                        file_result['message'] = '跳过重复文件（相同报告编号）'
                        file_result['equipment_name'] = equipment.name
                        skipped_count += 1
                        results.append(file_result)
                        print(f"跳过重复文件（报告编号）: {pdf_file.name}")
                        continue

                # 保存上传文件记录
                uploaded_file = UploadedFile.objects.create(
                    file=pdf_file,
                    original_filename=pdf_file.name,
                    file_type='pdf',
                    file_size=pdf_file.size,
                    processing_status='processing'
                )

                # 尝试提取多次测量数据
                multi_data = extract_multi_measurement_data_enhanced(md_content)
                has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1

                if has_multiple_measurements and len(multi_data['sample_dates']) > 1:
                    # 处理多次测量数据
                    print(f"检测到多次测量数据: {len(multi_data['sample_dates'])} 个测量")
                    
                    # 如果启用了"仅上传不重复日期"，过滤掉已存在的日期
                    if upload_non_duplicate_only and new_dates:
                        print(f"仅上传不重复日期: 新日期 {len(new_dates)} 个，跳过重复日期 {len(duplicate_dates)} 个")
                        # 过滤multi_data，只保留新日期的数据
                        filtered_multi_data = {
                            'sample_dates': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in new_dates],
                            'measurements': multi_data.get('measurements', [])
                        }
                        reports_data = create_multiple_reports_enhanced(filtered_multi_data, equipment, report_number_base)
                    elif upload_non_duplicate_only and not new_dates:
                        # 所有日期都已存在
                        file_result['status'] = 'skipped'
                        file_result['message'] = f'所有采样日期({len(duplicate_dates)}个)都已存在，未创建新报告'
                        file_result['equipment_name'] = equipment.name
                        skipped_count += 1
                        results.append(file_result)
                        print(f"所有日期都已存在，跳过文件: {pdf_file.name}")
                        continue
                    else:
                        reports_data = create_multiple_reports_enhanced(multi_data, equipment, report_number_base)

                    # 创建报告详细信息列表
                    reports_details = []
                    created_count = 0
                    skipped_in_file = 0
                    
                    for report_data in reports_data:
                        report = OilInspectionReport.objects.create(
                            equipment=report_data['equipment'],
                            report_date=report_data['report_date'],
                            sample_date=report_data['sample_date'],
                            report_number=report_data['report_number'],
                            pdf_file=uploaded_file.file,
                            md_content=md_content,
                            is_processed=True
                        )

                        # 创建报告详情
                        report_detail = {
                            'report_id': report.id,
                            'report_number': report_data['report_number'],
                            'sample_date': report_data['sample_date'].strftime('%Y-%m-%d'),
                            'report_date': report_data['report_date'].strftime('%Y-%m-%d'),
                            'equipment_name': equipment.name,
                            'attraction_name': equipment.attraction.name if equipment.attraction else '',
                            'parameter_count': len(report_data['parameters']),
                            'parameters': []
                        }

                        # 保存参数并添加到详情中
                        for param_data in report_data['parameters']:
                            param = OilParameter.objects.create(
                                report=report,
                                parameter_name=param_data['parameter_name'],
                                parameter_value=param_data['parameter_value'],
                                unit=param_data['unit'],
                                standard_range=param_data['standard_range'],
                                is_normal=param_data['is_normal']
                            )

                            # 添加参数到详情列表
                            report_detail['parameters'].append({
                                'name': param_data['parameter_name'],
                                'value': param_data['parameter_value'],
                                'unit': param_data['unit'],
                                'standard_range': param_data['standard_range'],
                                'is_normal': param_data['is_normal']
                            })

                        reports_details.append(report_detail)

                    file_result['report_count'] = len(reports_data)
                    file_result['reports_details'] = reports_details
                    
                    # 构建消息，包含重复日期信息
                    if upload_non_duplicate_only and duplicate_dates:
                        file_result['message'] = f'成功创建 {len(reports_data)} 个报告，跳过 {len(duplicate_dates)} 个已存在的采样日期'
                        file_result['duplicate_dates'] = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in duplicate_dates]
                        file_result['new_dates'] = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in new_dates]
                    else:
                        file_result['message'] = f'成功创建 {len(reports_data)} 个报告，共 {len(reports_details)} 个测试记录'

                else:
                    # 单次测量处理 - 检查是否启用了"仅上传不重复日期"
                    if upload_non_duplicate_only and duplicate_dates:
                        file_result['status'] = 'skipped'
                        file_result['message'] = f'采样日期 {duplicate_dates[0]} 已存在，未创建新报告'
                        file_result['equipment_name'] = equipment.name
                        skipped_count += 1
                        results.append(file_result)
                        print(f"单次测量日期已存在，跳过: {pdf_file.name}")
                        continue
                    
                    print(f"处理单次测量数据")

                    # 解析油品参数
                    parameters = parse_oil_parameters(md_content)

                    # 创建报告
                    report = OilInspectionReport.objects.create(
                        equipment=equipment,
                        report_date=equipment_info.get('sample_date', datetime.now().date()),
                        sample_date=equipment_info.get('sample_date', datetime.now().date()),
                        report_number=report_number_base,
                        pdf_file=uploaded_file.file,
                        md_content=md_content,
                        is_processed=True
                    )

                    # 创建报告详情
                    report_detail = {
                        'report_id': report.id,
                        'report_number': report_number_base,
                        'sample_date': equipment_info.get('sample_date', datetime.now().date()).strftime('%Y-%m-%d'),
                        'report_date': equipment_info.get('sample_date', datetime.now().date()).strftime('%Y-%m-%d'),
                        'equipment_name': equipment.name,
                        'attraction_name': equipment.attraction.name if equipment.attraction else '',
                        'parameter_count': len(parameters),
                        'parameters': []
                    }

                    # 保存参数并添加到详情中
                    for param in parameters:
                        param_obj = OilParameter.objects.create(
                            report=report,
                            parameter_name=param['name'],
                            parameter_value=param['value'],
                            unit=param['unit'],
                            standard_range=param.get('standard_range', ''),
                            is_normal=param.get('is_normal', True)
                        )

                        # 添加参数到详情列表
                        report_detail['parameters'].append({
                            'name': param['name'],
                            'value': param['value'],
                            'unit': param['unit'],
                            'standard_range': param.get('standard_range', ''),
                            'is_normal': param.get('is_normal', True)
                        })

                    file_result['report_count'] = 1
                    file_result['reports_details'] = [report_detail]
                    file_result['message'] = '成功创建 1 个报告，1 个测试记录'

                # 更新上传文件状态
                uploaded_file.processed = True
                uploaded_file.processing_status = 'completed'
                uploaded_file.save()

                file_result['status'] = 'success'
                success_count += 1
                print(f"✅ 文件处理成功: {pdf_file.name}")

            except Exception as e:
                error_msg = str(e)
                print(f"❌ 文件处理失败: {pdf_file.name} - {error_msg}")

                file_result['status'] = 'error'
                file_result['error'] = error_msg
                error_count += 1

                # 如果设置了遇到错误时停止，则终止处理
                if not continue_on_error:
                    print(f"遇到错误，停止批量处理")
                    break

                # 更新上传文件状态（如果已创建）
                try:
                    if 'uploaded_file' in locals():
                        uploaded_file.processing_status = 'failed'
                        uploaded_file.error_message = error_msg
                        uploaded_file.save()
                except:
                    pass

            results.append(file_result)
            processed_count += 1

        # 创建表格格式的结果数据
        table_results = []
        for file_result in results:
            if file_result['status'] == 'success' and 'reports_details' in file_result:
                # 为每个测试记录创建一行
                for report_detail in file_result['reports_details']:
                    attraction_name = report_detail.get('attraction_name', '')
                    equipment_name = report_detail.get('equipment_name', '')
                    test_date = report_detail.get('sample_date', '')

                    # 创建 attraction_spot_test_date 格式
                    attraction_spot_test_date = f"{attraction_name}_{equipment_name}_{test_date}"

                    # 创建行数据
                    row_data = {
                        'attraction_spot_test_date': attraction_spot_test_date,
                        'attraction_name': attraction_name,
                        'equipment_name': equipment_name,
                        'test_date': test_date,
                        'report_id': report_detail.get('report_id'),
                        'report_number': report_detail.get('report_number'),
                        'parameter_count': report_detail.get('parameter_count', 0),
                        'status': 'success',
                        'message': f"成功创建 {report_detail.get('parameter_count', 0)} 个参数",
                        'filename': file_result['filename']
                    }
                    table_results.append(row_data)
            elif file_result['status'] == 'error':
                # 为错误文件创建一行
                attraction_spot_test_date = f"错误_{file_result['filename']}"
                row_data = {
                    'attraction_spot_test_date': attraction_spot_test_date,
                    'attraction_name': '',
                    'equipment_name': '',
                    'test_date': '',
                    'report_id': '',
                    'report_number': '',
                    'parameter_count': 0,
                    'status': 'error',
                    'message': file_result.get('error', '处理失败'),
                    'filename': file_result['filename']
                }
                table_results.append(row_data)
            elif file_result['status'] == 'skipped':
                # 为跳过文件创建一行
                attraction_spot_test_date = f"跳过_{file_result['filename']}"
                row_data = {
                    'attraction_spot_test_date': attraction_spot_test_date,
                    'attraction_name': '',
                    'equipment_name': '',
                    'test_date': '',
                    'report_id': '',
                    'report_number': '',
                    'parameter_count': 0,
                    'status': 'skipped',
                    'message': file_result.get('message', '跳过处理'),
                    'filename': file_result['filename']
                }
                table_results.append(row_data)

        # 生成处理结果摘要
        summary = {
            'total_files': len(pdf_files),
            'processed_count': processed_count,
            'success_count': success_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'reports_created': sum(r['report_count'] for r in results if r['status'] == 'success'),
            'test_records_created': sum(len(r.get('reports_details', [])) for r in results if r['status'] == 'success'),
            'table_rows': len(table_results)
        }

        print(f"\n📊 批量处理完成:")
        print(f"   总文件数: {summary['total_files']}")
        print(f"   已处理: {summary['processed_count']}")
        print(f"   成功: {summary['success_count']}")
        print(f"   跳过: {summary['skipped_count']}")
        print(f"   错误: {summary['error_count']}")
        print(f"   创建报告: {summary['reports_created']}")
        print(f"   创建测试记录: {summary['test_records_created']}")
        print(f"   表格行数: {summary['table_rows']}")

        return JsonResponse({
            'success': True,
            'message': f'批量处理完成，成功处理 {success_count} 个文件',
            'results': results,  # 保留原始结果格式
            'table_results': table_results,  # 新增表格格式结果
            'summary': summary
        })

    # GET请求时显示批量上传页面
    attractions = Attraction.objects.all().order_by('name')
    return render(request, 'oil_records/upload_simple.html', {'attractions': attractions})


def batch_upload_stream(request):
    """SSE 流式批量上传 - 实时推送每个文件的处理状态"""
    import uuid
    
    task_id = request.GET.get('task_id')
    print(f"SSE连接请求: task_id={task_id}")
    
    if not task_id or task_id not in batch_upload_tasks:
        print(f"无效的任务ID: {task_id}, 可用任务: {list(batch_upload_tasks.keys())}")
        return JsonResponse({'success': False, 'error': '无效的任务ID'})
    
    task_queue = batch_upload_tasks[task_id]
    print(f"SSE连接已建立: task_id={task_id}")
    
    def event_stream():
        """生成 SSE 事件流"""
        print(f"开始SSE事件流: task_id={task_id}")
        while True:
            try:
                # 从队列获取消息，超时1秒
                message = task_queue.get(timeout=1)
                print(f"SSE发送消息: {message.get('type')} - {message.get('filename', 'N/A')}")
                
                # 发送 SSE 事件
                yield f"data: {json.dumps(message)}\n\n"
                
                # 如果是完成或错误消息，结束流
                if message.get('type') in ['complete', 'error']:
                    print(f"SSE流结束: {message.get('type')}")
                    break
                    
            except queue.Empty:
                # 发送心跳保持连接
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                continue
            except Exception as e:
                print(f"SSE错误: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
        
        # 清理任务数据
        if task_id in batch_upload_tasks:
            del batch_upload_tasks[task_id]
            print(f"任务数据已清理: {task_id}")
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def batch_upload_async(request):
    """启动异步批量上传任务"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支持POST请求'})
    
    if 'pdf_files' not in request.FILES:
        return JsonResponse({'success': False, 'error': '请选择要上传的PDF文件'})
    
    pdf_files = request.FILES.getlist('pdf_files')
    if not pdf_files:
        return JsonResponse({'success': False, 'error': '没有有效的PDF文件'})
    
    # 生成任务ID
    import uuid
    from io import BytesIO
    task_id = str(uuid.uuid4())
    
    # 创建消息队列
    task_queue = queue.Queue()
    batch_upload_tasks[task_id] = task_queue
    
    # 获取上传选项
    options = {
        'auto_upload': request.POST.get('auto_upload') == 'true',
        'skip_duplicates': request.POST.get('skip_duplicates') == 'true',
        'continue_on_error': request.POST.get('continue_on_error') == 'true',
        'upload_non_duplicate_only': request.POST.get('upload_non_duplicate_only') == 'true'
    }
    
    # 在启动后台线程前，先将文件内容读取到内存中
    # 因为 request.FILES 中的文件对象在请求结束后会被关闭
    file_data_list = []
    for pdf_file in pdf_files:
        file_data_list.append({
            'name': pdf_file.name,
            'content': pdf_file.read(),
            'size': pdf_file.size
        })
    
    # 在后台线程中处理文件
    def process_files():
        """后台处理文件并推送状态"""
        try:
            # 发送开始消息
            task_queue.put({
                'type': 'start',
                'total': len(file_data_list),
                'message': f'开始处理 {len(file_data_list)} 个文件'
            })
            
            # 处理每个文件
            for i, file_data in enumerate(file_data_list):
                # 发送处理开始消息
                task_queue.put({
                    'type': 'processing',
                    'index': i,
                    'filename': file_data['name'],
                    'progress': f'{i+1}/{len(file_data_list)}',
                    'message': f'正在处理: {file_data['name']}'
                })
                
                try:
                    # 创建内存中的文件对象
                    from django.core.files.uploadedfile import InMemoryUploadedFile
                    pdf_file = InMemoryUploadedFile(
                        file=BytesIO(file_data['content']),
                        field_name='pdf_files',
                        name=file_data['name'],
                        content_type='application/pdf',
                        size=file_data['size'],
                        charset=None
                    )
                    
                    # 处理单个文件
                    result = process_single_file(pdf_file, options, i)
                    
                    # 发送成功消息
                    task_queue.put({
                        'type': 'file_complete',
                        'index': i,
                        'filename': file_data['name'],
                        'status': result['status'],
                        'message': result.get('message', ''),
                        'equipment_name': result.get('equipment_name', ''),
                        'report_count': result.get('report_count', 0),
                        'duplicate_dates': result.get('duplicate_dates', []),
                        'new_dates': result.get('new_dates', [])
                    })
                    
                except Exception as e:
                    # 发送错误消息
                    task_queue.put({
                        'type': 'file_error',
                        'index': i,
                        'filename': file_data['name'],
                        'status': 'error',
                        'message': str(e)
                    })
                    
                    if not options['continue_on_error']:
                        break
            
            # 发送完成消息
            task_queue.put({
                'type': 'complete',
                'message': '所有文件处理完成'
            })
            
        except Exception as e:
            task_queue.put({
                'type': 'error',
                'message': f'处理过程出错: {str(e)}'
            })
    
    # 启动后台线程
    thread = threading.Thread(target=process_files)
    thread.daemon = True
    thread.start()
    
    print(f"批量上传任务已启动: task_id={task_id}, 文件数={len(file_data_list)}")
    
    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'message': '批量上传任务已启动'
    })


def process_single_file(pdf_file, options, index):
    """处理单个文件"""
    result = {
        'filename': pdf_file.name,
        'status': 'pending',
        'message': '',
        'equipment_name': '',
        'attraction_name': '',
        'report_count': 0,
        'error': ''
    }
    
    try:
        # 检查文件大小
        if pdf_file.size > 50 * 1024 * 1024:
            raise ValueError(f"文件太大: {pdf_file.size / 1024 / 1024:.1f}MB")
        
        # OCR处理
        pdf_file.seek(0)
        md_content = call_mineru_api(pdf_file)
        
        # 智能提取设备信息
        from smart_equipment_extraction import extract_equipment_info_complete, find_or_create_equipment
        from enhanced_multi_measurement_extraction import extract_multi_measurement_data_enhanced, create_multiple_reports_enhanced
        
        equipment_info = extract_equipment_info_complete(md_content, pdf_file.name)
        equipment_info['filename'] = pdf_file.name
        equipment, created = find_or_create_equipment(equipment_info)
        
        result['equipment_name'] = equipment.name
        result['attraction_name'] = equipment.attraction.name if equipment.attraction else '未知景点'
        
        # 生成报告编号
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_number_base = f"BATCH_{timestamp}_{index+1}"
        
        # 保存上传文件记录前重置文件指针
        pdf_file.seek(0)
        uploaded_file = UploadedFile.objects.create(
            file=pdf_file,
            original_filename=pdf_file.name,
            file_type='pdf',
            file_size=pdf_file.size,
            processing_status='processing'
        )
        
        # 提取多次测量数据
        multi_data = extract_multi_measurement_data_enhanced(md_content)
        has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1
        
        # 检查重复日期
        duplicate_dates = []
        new_dates = []
        
        if has_multiple_measurements and multi_data['sample_dates']:
            sample_dates = []
            for date_str in multi_data['sample_dates']:
                if isinstance(date_str, str):
                    try:
                        sample_dates.append(datetime.strptime(date_str, '%Y-%m-%d').date())
                    except ValueError:
                        continue
                else:
                    sample_dates.append(date_str)
            
            existing_reports = OilInspectionReport.objects.filter(
                equipment=equipment,
                sample_date__in=sample_dates
            ).values_list('sample_date', flat=True)
            
            existing_dates_set = set(existing_reports)
            new_dates = [date for date in sample_dates if date not in existing_dates_set]
            duplicate_dates = [date for date in sample_dates if date in existing_dates_set]
        
        # 根据选项处理
        if options['skip_duplicates'] and not options['upload_non_duplicate_only']:
            if duplicate_dates:
                result['status'] = 'skipped'
                result['message'] = f'跳过重复文件（设备已有{duplicate_dates[0]}等日期的报告）'
                return result
        
        # 创建报告
        if has_multiple_measurements and len(multi_data['sample_dates']) > 1:
            # 处理多次测量
            if options['upload_non_duplicate_only'] and new_dates:
                filtered_multi_data = {
                    'sample_dates': [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in new_dates],
                    'measurements': multi_data.get('measurements', [])
                }
                reports_data = create_multiple_reports_enhanced(filtered_multi_data, equipment, report_number_base)
            elif options['upload_non_duplicate_only'] and not new_dates:
                result['status'] = 'skipped'
                result['message'] = f'所有采样日期({len(duplicate_dates)}个)都已存在'
                result['duplicate_dates'] = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in duplicate_dates]
                return result
            else:
                reports_data = create_multiple_reports_enhanced(multi_data, equipment, report_number_base)
            
            # 创建报告
            for report_data in reports_data:
                report = OilInspectionReport.objects.create(
                    equipment=report_data['equipment'],
                    report_date=report_data['report_date'],
                    sample_date=report_data['sample_date'],
                    report_number=report_data['report_number'],
                    pdf_file=uploaded_file.file,
                    md_content=md_content,
                    is_processed=True
                )
                
                # 保存参数
                for param_data in report_data['parameters']:
                    OilParameter.objects.create(
                        report=report,
                        parameter_name=param_data['parameter_name'],
                        parameter_value=param_data['parameter_value'],
                        unit=param_data['unit'],
                        standard_range=param_data['standard_range'],
                        is_normal=param_data['is_normal']
                    )
            
            result['status'] = 'success'
            result['report_count'] = len(reports_data)
            result['duplicate_dates'] = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in duplicate_dates]
            result['new_dates'] = [d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in new_dates]
            
            if options['upload_non_duplicate_only'] and duplicate_dates:
                result['message'] = f'成功创建 {len(reports_data)} 个报告，跳过 {len(duplicate_dates)} 个已存在的采样日期'
            else:
                result['message'] = f'成功创建 {len(reports_data)} 个报告'
        else:
            # 单次测量
            if options['upload_non_duplicate_only'] and duplicate_dates:
                result['status'] = 'skipped'
                result['message'] = f'采样日期 {duplicate_dates[0]} 已存在'
                return result
            
            # 解析参数
            parameters = parse_oil_parameters(md_content)
            
            # 创建报告
            report = OilInspectionReport.objects.create(
                equipment=equipment,
                report_date=equipment_info.get('sample_date', datetime.now().date()),
                sample_date=equipment_info.get('sample_date', datetime.now().date()),
                report_number=report_number_base,
                pdf_file=uploaded_file.file,
                md_content=md_content,
                is_processed=True
            )
            
            # 保存参数
            for param in parameters:
                OilParameter.objects.create(
                    report=report,
                    parameter_name=param['name'],
                    parameter_value=param['value'],
                    unit=param['unit'],
                    standard_range=param.get('standard_range', ''),
                    is_normal=param.get('is_normal', True)
                )
            
            result['status'] = 'success'
            result['report_count'] = 1
            result['message'] = '成功创建 1 个报告'
        
        # 更新上传文件状态
        uploaded_file.processed = True
        uploaded_file.processing_status = 'completed'
        uploaded_file.save()
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        raise
    
    return result


def ocr_preview_data(request, pdf_file):
    """OCR预览数据处理 - 只处理和展示，不保存到数据库"""
    try:
        # 重置文件指针到开始位置
        pdf_file.seek(0)
        
        # 调用mineru-api进行OCR处理
        print(f"开始OCR预览处理文件: {pdf_file.name}")
        md_content = call_mineru_api(pdf_file)
        print(f"OCR处理完成，MD内容长度: {len(md_content)}")
        
        # 提取设备信息
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from smart_equipment_extraction import extract_equipment_info_complete
            equipment_info = extract_equipment_info_complete(md_content, pdf_file.name)
        except ImportError:
            equipment_info = {
                'equipment_name': '',
                'location': '',
                'equipment_type': '',
                'confidence': 0.0
            }
        
        # 提取油品参数
        parameters = parse_oil_parameters(md_content)
        
        # 尝试提取多次测量数据
        try:
            from enhanced_multi_measurement_extraction import extract_multi_measurement_data_enhanced
            multi_data = extract_multi_measurement_data_enhanced(md_content)
            has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1
        except ImportError:
            try:
                from multi_measurement_extraction import extract_multi_measurement_data
                multi_data = extract_multi_measurement_data(md_content)
                has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1
            except ImportError:
                multi_data = {}
                has_multiple_measurements = False
        
        # 将OCR预览数据存储到session中
        session_data = {
            'filename': pdf_file.name,
            'md_content': md_content,
            'equipment_info': equipment_info,
            'parameters': parameters,
            'has_multiple_measurements': has_multiple_measurements,
            'multi_data': {},
            'processing_type': 'ocr_preview'  # 标记为OCR预览类型
        }
        
        # 处理多次测量数据，确保日期可以序列化
        if has_multiple_measurements and multi_data:
            # 预处理测量数据，添加状态信息
            processed_measurements = []
            for measurement in multi_data.get('measurements', []):
                # 计算状态
                has_abnormal = any(is_normal == False for is_normal in measurement.get('is_normal', []))
                processed_measurement = measurement.copy()
                processed_measurement['has_abnormal'] = has_abnormal
                
                # 处理None值，确保在前端正确显示
                processed_values = []
                for value in processed_measurement.get('values', []):
                    if value is None:
                        processed_values.append(None)  # 保持None，让前端模板处理
                    else:
                        processed_values.append(value)
                processed_measurement['values'] = processed_values
                
                processed_measurements.append(processed_measurement)
            
            session_data['multi_data'] = {
                'sample_dates': [date.isoformat() if hasattr(date, 'isoformat') else str(date) for date in multi_data.get('sample_dates', [])],
                'measurements': processed_measurements,
                'parameters_by_date': multi_data.get('parameters_by_date', {}),
                'raw_measurements': multi_data.get('raw_measurements', [])
            }
        
        request.session['ocr_preview'] = session_data
        
        # 返回JSON响应给AJAX请求
        return JsonResponse({
            'success': True,
            'redirect': reverse('oil_records:ocr_preview_display'),
            'message': 'OCR处理完成，正在跳转到预览页面'
        })
        
    except Exception as e:
        print(f"OCR预览处理失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'OCR预览处理失败：{str(e)}'
        })

def preview_upload_data(request, pdf_file):
    """预览上传数据"""
    try:
        # 重置文件指针到开始位置
        pdf_file.seek(0)
        
        # 调用mineru-api进行OCR处理
        print(f"开始预览处理文件: {pdf_file.name}")
        md_content = call_mineru_api(pdf_file)
        print(f"OCR处理完成，MD内容长度: {len(md_content)}")
        
        # 提取设备信息
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from smart_equipment_extraction import extract_equipment_info_complete
            equipment_info = extract_equipment_info_complete(md_content, pdf_file.name)
        except ImportError:
            equipment_info = {
                'equipment_name': '',
                'location': '',
                'equipment_type': '',
                'confidence': 0.0
            }
        
        # 提取油品参数
        parameters = parse_oil_parameters(md_content)
        
        # 尝试提取多次测量数据
        try:
            from enhanced_multi_measurement_extraction import extract_multi_measurement_data_enhanced
            multi_data = extract_multi_measurement_data_enhanced(md_content)
            has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1
        except ImportError:
            try:
                from multi_measurement_extraction import extract_multi_measurement_data
                multi_data = extract_multi_measurement_data(md_content)
                has_multiple_measurements = multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1
            except ImportError:
                multi_data = {}
                has_multiple_measurements = False
        
        # 将预览数据存储到session中（不包含文件内容）
        # 确保所有数据都可以JSON序列化
        session_data = {
            'filename': pdf_file.name,
            'md_content': md_content,
            'equipment_info': equipment_info,
            'parameters': parameters,
            'has_multiple_measurements': has_multiple_measurements,
            'multi_data': {}
        }
        
        # 处理多次测量数据，确保日期可以序列化
        if has_multiple_measurements and multi_data:
            session_data['multi_data'] = {
                'sample_dates': [date.isoformat() if hasattr(date, 'isoformat') else str(date) for date in multi_data.get('sample_dates', [])],
                'report_dates': [date.isoformat() if hasattr(date, 'isoformat') else str(date) for date in multi_data.get('report_dates', [])],
                'parameters_by_date': multi_data.get('parameters_by_date', {}),
                'raw_measurements': multi_data.get('raw_measurements', [])
            }
        
        request.session['upload_preview'] = session_data
        
        # 返回JSON响应给AJAX请求
        return JsonResponse({
            'success': True,
            'redirect': reverse('oil_records:upload_preview'),
            'message': '预览数据生成成功'
        })
        
    except Exception as e:
        print(f"预览处理失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'预览处理失败：{str(e)}'
        })

def confirm_upload_data(request):
    """确认上传数据"""
    if request.method != 'POST':
        messages.error(request, '请使用POST方法提交数据')
        return redirect('oil_records:upload_simple')
    
    # 检查是否有文件上传
    if 'pdf_file' not in request.FILES:
        messages.error(request, '请重新选择PDF文件')
        return redirect('oil_records:upload_simple')
    
    pdf_file = request.FILES['pdf_file']
    
    try:
        # 保存上传的文件记录
        uploaded_file = UploadedFile.objects.create(
            file=pdf_file,
            original_filename=pdf_file.name,
            file_type='pdf',
            file_size=pdf_file.size,
            processing_status='pending'
        )
        
        # 调用mineru-api进行OCR处理
        print(f"开始确认处理文件: {pdf_file.name}")
        md_content = call_mineru_api(pdf_file)
        print(f"OCR处理完成，MD内容长度: {len(md_content)}")
        
        # 获取用户确认的设备信息
        confirmed_equipment = request.POST.get('confirmed_equipment')
        if confirmed_equipment:
            # 用户选择了现有设备
            equipment = get_object_or_404(Equipment, id=confirmed_equipment)
        else:
            # 使用自动识别的设备信息
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            try:
                from smart_equipment_extraction import extract_equipment_info_complete, find_or_create_equipment
                equipment_info = extract_equipment_info_complete(md_content, pdf_file.name)
                
                if equipment_info['confidence'] > 0.6:
                    equipment, _ = find_or_create_equipment(equipment_info)
                else:
                    messages.error(request, '设备信息置信度不足，请手动选择设备')
                    return redirect('oil_records:upload_preview')
            except ImportError:
                messages.error(request, '无法自动识别设备信息，请手动选择设备')
                return redirect('oil_records:upload_preview')
        
        # 尝试提取多次测量数据
        try:
            from enhanced_multi_measurement_extraction import extract_multi_measurement_data_enhanced
            multi_data = extract_multi_measurement_data_enhanced(md_content)
        except ImportError:
            try:
                from multi_measurement_extraction import extract_multi_measurement_data
                multi_data = extract_multi_measurement_data(md_content)
            except ImportError:
                multi_data = {}
        
        # 处理OCR结果并保存到数据库
        process_ocr_result_with_equipment(
            uploaded_file, 
            md_content, 
            equipment,
            multi_data,
            pdf_file.name
        )
        
        # 清理session数据
        if 'upload_preview' in request.session:
            del request.session['upload_preview']
        
        # 获取刚创建的报告来统计参数数量
        reports = OilInspectionReport.objects.filter(pdf_file=uploaded_file.file).order_by('-created_at')
        total_params = sum(OilParameter.objects.filter(report=report).count() for report in reports)
        
        messages.success(request, f'数据导入成功！创建了{reports.count()}个报告，解析了{total_params}个参数。')
        return redirect('oil_records:dashboard')
        
    except Exception as e:
        print(f"确认导入失败: {e}")
        uploaded_file.processing_status = 'failed'
        uploaded_file.error_message = str(e)
        uploaded_file.save()
        messages.error(request, f'导入失败：{str(e)}')
        return redirect('oil_records:upload_preview')

def process_ocr_result_with_equipment(uploaded_file, md_content, equipment, multi_data, filename=None):
    """使用指定设备处理OCR结果并保存到数据库"""
    try:
        # 获取报告编号（可选）
        report_number = ''
        
        # 尝试使用多次测量提取
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from enhanced_multi_measurement_extraction import create_multiple_reports_enhanced
            
            if multi_data.get('sample_dates') and len(multi_data['sample_dates']) > 1:
                # 多次测量情况
                print(f"检测到 {len(multi_data['sample_dates'])} 次测量结果")
                
                # 创建多个报告
                reports_data = create_multiple_reports_enhanced(multi_data, equipment, report_number)
                
                created_reports = []
                for report_data in reports_data:
                    # 创建油品检测报告
                    report = OilInspectionReport.objects.create(
                        equipment=equipment,
                        report_date=report_data['report_date'],
                        sample_date=report_data['sample_date'],
                        report_number=report_data['report_number'],
                        pdf_file=uploaded_file.file,
                        md_content=md_content,
                        is_processed=True
                    )
                    
                    # 保存油品参数
                    for param_data in report_data['parameters']:
                        OilParameter.objects.create(
                            report=report,
                            parameter_name=param_data['parameter_name'],
                            parameter_value=param_data['parameter_value'],
                            unit=param_data['unit'],
                            standard_range=param_data['standard_range'],
                            is_normal=param_data['is_normal']
                        )
                    
                    created_reports.append(report)
                
                print(f"成功创建 {len(created_reports)} 个报告")
                
            else:
                # 单次测量情况
                create_single_report(uploaded_file, md_content, equipment, report_number)
        
        except ImportError:
            # 如果多次测量提取不可用，使用单次测量
            create_single_report(uploaded_file, md_content, equipment, report_number)
        
        # 更新上传文件状态
        uploaded_file.processed = True
        uploaded_file.processing_status = 'completed'
        uploaded_file.save()
        
    except Exception as e:
        uploaded_file.processing_status = 'failed'
        uploaded_file.error_message = str(e)
        uploaded_file.save()
        raise e

def create_single_report(uploaded_file, md_content, equipment, report_number):
    """创建单个报告"""
    # 创建油品检测报告
    report = OilInspectionReport.objects.create(
        equipment=equipment,
        report_date=timezone.now().date(),
        sample_date=timezone.now().date(),
        report_number=report_number,
        pdf_file=uploaded_file.file,
        md_content=md_content,
        is_processed=True
    )
    
    # 解析MD内容提取油品参数
    parameters = parse_oil_parameters(md_content)
    
    # 保存油品参数
    for param in parameters:
        OilParameter.objects.create(
            report=report,
            parameter_name=param['name'],
            parameter_value=param['value'],
            unit=param['unit'],
            standard_range=param.get('standard_range', ''),
            is_normal=param.get('is_normal', True)
        )
    
    print("成功创建单个报告")

def ocr_preview_display(request):
    """显示OCR预览页面 - 只展示处理结果，不保存到数据库"""
    ocr_data = request.session.get('ocr_preview')
    if not ocr_data:
        messages.error(request, 'OCR预览数据已过期，请重新上传文件')
        return redirect('oil_records:upload_report_simple')
    
    # 获取所有景点供用户选择
    attractions = Attraction.objects.all().order_by('name')
    
    # 智能匹配默认景点和设备
    default_attraction_id = None
    default_equipment_id = None
    equipment_info = ocr_data.get('equipment_info', {})
    
    # 使用修复的智能匹配函数
    if equipment_info:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from smart_equipment_extraction import simple_match_equipment
            
            # 获取文件名
            filename = ocr_data.get('filename', '')
            
            # 使用智能匹配函数
            matched_equipment_info = simple_match_equipment(equipment_info, filename)
            
            # 如果匹配成功，设置默认值
            if matched_equipment_info.get('matched_equipment_id'):
                default_attraction_id = matched_equipment_info['matched_attraction_id']
                default_equipment_id = matched_equipment_info['matched_equipment_id']
                print(f"智能匹配成功：景点 {matched_equipment_info.get('matched_attraction_name')}, 设备 {matched_equipment_info.get('matched_equipment_name')}")
            else:
                print(f"智能匹配失败，设备信息：{equipment_info}")
                
        except ImportError:
            print("智能匹配模块不可用，使用简单匹配")
            # 回退到简单匹配逻辑
            equipment_name = equipment_info.get('equipment_name', '').lower()
            location = equipment_info.get('location', '').lower()
            
            # 首先尝试精确匹配设备名称
            matched_equipment = None
            if equipment_name:
                matched_equipment = Equipment.objects.filter(
                    name__icontains=equipment_name
                ).first()
            
            # 如果精确匹配失败，尝试模糊匹配
            if not matched_equipment and equipment_name:
                # 提取设备名称的关键部分进行匹配
                name_parts = equipment_name.split()
                for part in name_parts:
                    if len(part) > 2:  # 只匹配长度大于2的部分
                        matched_equipment = Equipment.objects.filter(
                            name__icontains=part
                        ).first()
                        if matched_equipment:
                            break
            
            # 如果还是没找到，尝试结合位置信息匹配
            if not matched_equipment and location:
                matched_equipment = Equipment.objects.filter(
                    location__icontains=location
                ).first()
            
            # 如果找到了匹配的设备，设置默认值
            if matched_equipment:
                default_attraction_id = matched_equipment.attraction.id
                default_equipment_id = matched_equipment.id
                print(f"简单匹配成功：景点 {matched_equipment.attraction.name}, 设备 {matched_equipment.name}")
            else:
                print(f"简单匹配失败，设备信息：{equipment_info}")
    
    # 构建设备信息显示数据
    display_equipment_info = equipment_info.copy()
    
    # 如果有智能匹配结果，添加置信度和匹配详情信息
    if default_attraction_id and default_equipment_id:
        # 获取匹配的设备和景点信息
        try:
            matched_attraction = Attraction.objects.get(id=default_attraction_id)
            matched_equipment = Equipment.objects.get(id=default_equipment_id)
            
            display_equipment_info['confidence'] = 0.9  # 高置信度
            display_equipment_info['matched_attraction_id'] = default_attraction_id
            display_equipment_info['matched_equipment_id'] = default_equipment_id
            
            # 添加匹配详情，供模板显示
            display_equipment_info['match_details'] = {
                'matched_attraction': matched_attraction.name,
                'matched_equipment': matched_equipment.name
            }
            
            # 如果原始提取信息不完整，用匹配结果补充
            if not display_equipment_info.get('equipment_name'):
                display_equipment_info['equipment_name'] = matched_equipment.name
            if not display_equipment_info.get('location'):
                display_equipment_info['location'] = matched_equipment.location
            if not display_equipment_info.get('equipment_type'):
                display_equipment_info['equipment_type'] = matched_equipment.equipment_type
                
        except (Attraction.DoesNotExist, Equipment.DoesNotExist):
            display_equipment_info['confidence'] = 0.7  # 中等置信度
    elif equipment_info.get('matched_equipment_id'):
        display_equipment_info['confidence'] = 0.8  # 中等置信度
    else:
        display_equipment_info['confidence'] = 0.3  # 低置信度
    
    # 添加提取方法信息
    display_equipment_info['extraction_method'] = '智能匹配算法 v2.1'

    context = {
        'ocr_data': ocr_data,
        'ocr_data_json': json.dumps(ocr_data, ensure_ascii=False),  # 提供JSON格式的数据
        'is_ocr_preview': True,  # 标记这是OCR预览页面
        'attractions': attractions,  # 添加景点数据
        'default_attraction_id': default_attraction_id,  # 默认景点ID
        'default_equipment_id': default_equipment_id,  # 默认设备ID
        'equipment_info': display_equipment_info,  # 设备信息用于显示
    }
    
    return render(request, 'oil_records/ocr_preview_display.html', context)

def upload_preview(request):
    """显示上传预览页面"""
    preview_data = request.session.get('upload_preview')
    if not preview_data:
        messages.error(request, '预览数据已过期，请重新上传文件')
        return redirect('oil_records:upload_simple')
    
    # 获取所有设备供用户选择
    equipment_list = Equipment.objects.all().order_by('attraction__name', 'name')
    
    context = {
        'preview_data': preview_data,
        'equipment_list': equipment_list,
    }
    
    return render(request, 'oil_records/upload_preview.html', context)

def call_mineru_api(pdf_file):
    """调用mineru-api进行OCR处理"""
    # 使用settings.py中配置的API地址
    api_url = settings.MINERU_API_URL
    
    # 重置文件指针到开始位置
    pdf_file.seek(0)
    
    # 读取文件内容
    file_content = pdf_file.read()
    
    # 重新创建文件对象以确保正确格式
    from io import BytesIO
    file_obj = BytesIO(file_content)
    
    # files参数需要是数组格式，根据OpenAPI规范
    files = [('files', (pdf_file.name, file_obj, 'application/pdf'))]
    
    # 指定输出目录到项目的md_files文件夹
    output_dir = os.path.join(settings.BASE_DIR, 'md_files')
    os.makedirs(output_dir, exist_ok=True)
    
    data = {
        'return_md': True,  # 返回markdown格式
        'lang_list': ['ch'],  # 中文识别
        'parse_method': 'auto',  # 自动解析
        'backend': 'pipeline',  # 使用pipeline后端
        'table_enable': True,  # 启用表格识别
        'formula_enable': True,  # 启用公式识别
        'output_dir': output_dir,  # 指定输出目录
        'is_json': False,  # 确保返回markdown而不是JSON
    }
    
    try:
        print(f"📞 调用mineru-api: {api_url}")
        print(f"📁 文件名: {pdf_file.name}")
        print(f"📏 文件大小: {len(file_content)} bytes")
        
        response = requests.post(api_url, files=files, data=data, timeout=300)
        print(f"📊 响应状态码: {response.status_code}")
        
        response.raise_for_status()
        
        # 处理mineru-api的响应
        result = response.json()
        print(f"📝 响应类型: {type(result)}")
        
        # 根据实际API响应格式处理
        if isinstance(result, dict):
            # 如果有markdown内容
            if 'md_content' in result:
                return result['md_content']
            elif 'results' in result:
                # 从results中提取第一个文件的md_content
                results = result.get('results', {})
                if results:
                    first_file = list(results.values())[0]
                    if 'md_content' in first_file:
                        return first_file['md_content']
            elif 'content' in result:
                return result['content']
            elif 'data' in result:
                return str(result['data'])
            else:
                # 返回整个JSON的字符串形式
                return json.dumps(result, ensure_ascii=False)
        else:
            return str(result)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API调用异常: {e}")
        raise Exception(f'API调用失败：{str(e)}')

def process_ocr_result(uploaded_file, md_content, form_data, filename=None):
    """处理OCR结果并保存到数据库"""
    try:
        # 尝试自动提取设备信息
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from smart_equipment_extraction import extract_equipment_info_complete, find_or_create_equipment
            
            # 从文件名和MD内容中提取设备信息
            equipment_info = extract_equipment_info_complete(md_content, filename)
            
            if equipment_info['confidence'] > 0.6:
                # 自动查找或创建设备
                equipment, equipment_created = find_or_create_equipment(equipment_info)
                print(f"自动{'创建' if equipment_created else '找到'}设备: {equipment.name}")
            else:
                # 如果自动提取置信度低，使用表单数据
                attraction_id = form_data.get('attraction')
                equipment_id = form_data.get('equipment')
                
                if not attraction_id or not equipment_id:
                    raise Exception("无法自动识别设备信息，请手动选择设备和景点")
                
                attraction = get_object_or_404(Attraction, id=attraction_id)
                equipment = get_object_or_404(Equipment, id=equipment_id)
                
        except ImportError:
            # 如果智能提取不可用，使用表单数据
            attraction_id = form_data.get('attraction')
            equipment_id = form_data.get('equipment')
            
            if not attraction_id or not equipment_id:
                raise Exception("请选择设备和景点")
            
            attraction = get_object_or_404(Attraction, id=attraction_id)
            equipment = get_object_or_404(Equipment, id=equipment_id)
        
        # 获取报告编号（可选）
        report_number = form_data.get('report_number', '')
        
        # 尝试使用多次测量提取
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            from multi_measurement_extraction import extract_multi_measurement_data, create_multiple_reports
            
            # 提取多次测量数据
            multi_data = extract_multi_measurement_data(md_content)
            
            if multi_data['sample_dates'] and len(multi_data['sample_dates']) > 1:
                # 多次测量情况
                print(f"检测到 {len(multi_data['sample_dates'])} 次测量结果")
                
                # 创建多个报告
                reports_data = create_multiple_reports(multi_data, equipment, report_number)
                
                created_reports = []
                for report_data in reports_data:
                    # 创建油品检测报告
                    report = OilInspectionReport.objects.create(
                        equipment=equipment,
                        report_date=report_data['report_date'],
                        sample_date=report_data['sample_date'],
                        report_number=report_data['report_number'],
                        pdf_file=uploaded_file.file,
                        md_content=md_content,
                        is_processed=True
                    )
                    
                    # 保存油品参数
                    for param_data in report_data['parameters']:
                        OilParameter.objects.create(
                            report=report,
                            parameter_name=param_data['parameter_name'],
                            parameter_value=param_data['parameter_value'],
                            unit=param_data['unit'],
                            standard_range=param_data['standard_range'],
                            is_normal=param_data['is_normal']
                        )
                    
                    created_reports.append(report)
                
                print(f"成功创建 {len(created_reports)} 个报告")
                
            else:
                # 单次测量情况，使用原始逻辑
                report_date = form_data.get('report_date')
                sample_date = form_data.get('sample_date')
                
                # 处理可能的空值
                if report_date:
                    report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
                else:
                    report_date = timezone.now().date()
                    
                if sample_date:
                    sample_date = datetime.strptime(sample_date, '%Y-%m-%d').date()
                else:
                    sample_date = timezone.now().date()
                
                # 创建油品检测报告
                report = OilInspectionReport.objects.create(
                    equipment=equipment,
                    report_date=report_date,
                    sample_date=sample_date,
                    report_number=report_number,
                    pdf_file=uploaded_file.file,
                    md_content=md_content,
                    is_processed=True
                )
                
                # 解析MD内容提取油品参数
                parameters = parse_oil_parameters(md_content)
                
                # 保存油品参数
                for param in parameters:
                    OilParameter.objects.create(
                        report=report,
                        parameter_name=param['name'],
                        parameter_value=param['value'],
                        unit=param['unit'],
                        standard_range=param.get('standard_range', ''),
                        is_normal=param.get('is_normal', True)
                    )
                
                print("成功创建单个报告")
        
        except ImportError:
            # 如果多次测量提取不可用，回退到原始方法
            print("多次测量提取不可用，使用原始方法")
            report_date = form_data.get('report_date')
            sample_date = form_data.get('sample_date')
            
            # 创建油品检测报告
            report = OilInspectionReport.objects.create(
                equipment=equipment,
                report_date=datetime.strptime(report_date, '%Y-%m-%d').date(),
                sample_date=datetime.strptime(sample_date, '%Y-%m-%d').date(),
                report_number=report_number,
                pdf_file=uploaded_file.file,
                md_content=md_content,
                is_processed=True
            )
            
            # 解析MD内容提取油品参数
            parameters = parse_oil_parameters(md_content)
            
            # 保存油品参数
            for param in parameters:
                OilParameter.objects.create(
                    report=report,
                    parameter_name=param['name'],
                    parameter_value=param['value'],
                    unit=param['unit'],
                    standard_range=param.get('standard_range', ''),
                    is_normal=param.get('is_normal', True)
                )
        
        # 更新上传文件状态
        uploaded_file.processed = True
        uploaded_file.processing_status = 'completed'
        uploaded_file.save()
        
    except Exception as e:
        uploaded_file.processing_status = 'failed'
        uploaded_file.error_message = str(e)
        uploaded_file.save()
        raise e

def parse_oil_parameters(md_content):
    """解析MD内容提取油品参数 - 使用智能提取方法"""
    # 导入智能参数提取函数
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from smart_parameter_extraction import extract_all_parameters_smart
        return extract_all_parameters_smart(md_content)
    except ImportError:
        # 如果智能提取不可用，回退到原始方法
        return parse_oil_parameters_fallback(md_content)

def parse_oil_parameters_fallback(md_content):
    """解析MD内容提取油品参数 - 回退方法"""
    parameters = []
    
    # 首先尝试解析HTML表格格式
    if '<table>' in md_content and '<td>' in md_content:
        return parse_html_table_parameters(md_content)
    
    # 然后尝试解析Markdown表格格式
    lines = md_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if '|' in line and not line.startswith('|---'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                try:
                    param_name = parts[1]
                    param_value = float(parts[2])
                    unit = parts[3]
                    standard_range = parts[4] if len(parts) > 4 else ''
                    
                    # 判断是否在标准范围内
                    is_normal = True
                    if standard_range and '-' in standard_range:
                        min_val, max_val = map(float, standard_range.split('-'))
                        is_normal = min_val <= param_value <= max_val
                    
                    parameters.append({
                        'name': param_name,
                        'value': param_value,
                        'unit': unit,
                        'standard_range': standard_range,
                        'is_normal': is_normal
                    })
                except (ValueError, IndexError):
                    continue
    
    return parameters

def parse_html_table_parameters(md_content):
    """解析HTML表格格式的油品参数"""
    parameters = []
    
    try:
        # 简单的HTML表格解析
        import re
        
        # 查找表格内容
        table_pattern = r'<table>(.*?)</table>'
        table_match = re.search(table_pattern, md_content, re.DOTALL)
        
        if not table_match:
            return parameters
            
        table_content = table_match.group(1)
        
        # 分割表格行
        rows = re.findall(r'<tr>(.*?)</tr>', table_content, re.DOTALL)
        
        for row in rows:
            # 分割单元格
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            
            # 清理单元格内容
            cleaned_cells = []
            for cell in cells:
                # 移除HTML标签和多余空白
                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                cleaned_cells.append(clean_cell)
            
            # 尝试解析参数行（通常包含参数名、值、单位等）
            if len(cleaned_cells) >= 3:
                # 寻找可能的参数行
                param_name = cleaned_cells[0]
                
                # 检查是否是参数名（包含常见油品参数关键词）
                oil_param_keywords = ['粘度', '水分', '酸值', '闪点', '倾点', '密度', '粘度指数', '污染度', '铁', '铜', '铝', '硅', '钠', '钒', '镍', 'Viscosity', 'Water', 'Acid', 'Flash', 'Density', 'Iron', 'Copper', 'Aluminum', 'Silicon', 'Sodium', 'Vanadium', 'Nickel']
                
                is_oil_param = any(keyword in param_name for keyword in oil_param_keywords)
                
                if is_oil_param:
                    try:
                        # 尝试提取数值
                        param_value = None
                        unit = ''
                        standard_range = ''
                        
                        # 在剩余单元格中寻找数值
                        for cell in cleaned_cells[1:]:
                            # 寻找数值
                            value_match = re.search(r'(\d+\.?\d*)', cell)
                            if value_match and param_value is None:
                                param_value = float(value_match.group(1))
                                # 提取单位
                                unit_match = re.search(r'([a-zA-Z°%]+)', cell)
                                if unit_match:
                                    unit = unit_match.group(1)
                            # 寻找标准范围
                            range_match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)', cell)
                            if range_match:
                                standard_range = f"{range_match.group(1)}-{range_match.group(2)}"
                        
                        if param_value is not None:
                            # 判断是否在标准范围内
                            is_normal = True
                            if standard_range and '-' in standard_range:
                                try:
                                    min_val, max_val = map(float, standard_range.split('-'))
                                    is_normal = min_val <= param_value <= max_val
                                except ValueError:
                                    pass
                            
                            parameters.append({
                                'name': param_name,
                                'value': param_value,
                                'unit': unit,
                                'standard_range': standard_range,
                                'is_normal': is_normal
                            })
                    except (ValueError, IndexError):
                        continue
        
    except Exception as e:
        print(f"HTML表格解析错误: {e}")
    
    return parameters

@require_http_methods(["GET"])
def get_equipment_api(request):
    """获取设备列表API"""
    attraction_id = request.GET.get('attraction_id')
    
    if attraction_id:
        equipment = Equipment.objects.filter(attraction_id=attraction_id).order_by('name')
    else:
        equipment = Equipment.objects.all().order_by('name')
    
    equipment_list = []
    for eq in equipment:
        equipment_list.append({
            'id': eq.id,
            'name': eq.name,
            'location': eq.location,
            'equipment_type': eq.equipment_type
        })
    
    return JsonResponse({'equipment': equipment_list})

@require_http_methods(["GET"])
def get_trends_api(request):
    """获取趋势数据API"""
    equipment_id = request.GET.get('equipment_id')
    parameter_name = request.GET.get('parameter_name')
    days = int(request.GET.get('days', 365))
    
    if not equipment_id or not parameter_name:
        return JsonResponse({'error': '缺少必要参数'}, status=400)
    
    # 获取指定天数内的数据
    start_date = timezone.now().date() - timedelta(days=days)
    
    parameters = OilParameter.objects.filter(
        report__equipment_id=equipment_id,
        parameter_name=parameter_name,
        report__report_date__gte=start_date
    ).order_by('report__report_date')
    
    trend_data = []
    for param in parameters:
        trend_data.append({
            'date': param.report.report_date.strftime('%Y-%m-%d'),
            'value': param.parameter_value,
            'unit': param.unit,
            'is_normal': param.is_normal
        })
    
    return JsonResponse({'trends': trend_data})

@require_http_methods(["GET"])
def get_all_trends_api(request):
    """获取设备所有油品参数趋势数据API"""
    equipment_id = request.GET.get('equipment_id')
    days = int(request.GET.get('days', 365))
    
    if not equipment_id:
        return JsonResponse({'error': '缺少设备ID参数'}, status=400)
    
    # 获取指定天数内的数据
    start_date = timezone.now().date() - timedelta(days=days)
    
    # 获取该设备所有参数
    parameters = OilParameter.objects.filter(
        report__equipment_id=equipment_id,
        report__report_date__gte=start_date
    ).order_by('report__report_date')
    
    # 按参数名分组
    all_trends = {}
    for param in parameters:
        param_name = param.parameter_name
        if param_name not in all_trends:
            all_trends[param_name] = []
        
        all_trends[param_name].append({
            'date': param.report.report_date.strftime('%Y-%m-%d'),
            'value': param.parameter_value,
            'unit': param.unit,
            'is_normal': param.is_normal
        })
    
    return JsonResponse({'all_trends': all_trends})

@require_http_methods(["GET"])
def get_table_data_api(request):
    """获取表格数据API - 横向展示：指标为行，时间为列"""
    equipment_id = request.GET.get('equipment_id')
    days = int(request.GET.get('days', 365))
    
    if not equipment_id:
        return JsonResponse({'error': '缺少设备ID参数'}, status=400)
    
    # 获取指定天数内的数据
    start_date = timezone.now().date() - timedelta(days=days)
    
    # 获取该设备所有报告日期（去重，按时间倒序）
    report_dates = OilInspectionReport.objects.filter(
        equipment_id=equipment_id,
        report_date__gte=start_date
    ).values_list('report_date', flat=True).distinct().order_by('-report_date')
    
    # 获取该设备所有参数
    parameters = OilParameter.objects.filter(
        report__equipment_id=equipment_id,
        report__report_date__gte=start_date
    ).select_related('report')
    
    # 按参数名称分组，收集不同时间的值
    param_data = {}
    
    def normalize_param_name(name):
        """标准化参数名称，基于关键词映射统一格式"""
        import re
        # 去除所有空格
        name = ''.join(name.split())
        # 将全角字符转为半角
        name = name.replace('／', '/').replace('，', ',').replace('。', '.').replace('（', '(').replace('）', ')')
        # 统一大小写
        name = name.lower()
        
        # 定义关键词映射表（按优先级排序）
        keyword_mappings = [
            # 粘度相关
            (r'viscosity.*40.*cst.*粘度', 'Viscosity 40°C'),
            (r'粘度.*40', 'Viscosity 40°C'),
            
            # WPI/PQ指数
            (r'pq.*index.*wpi.*pq指数', 'PQ Index (WPI)'),
            (r'pq.*wpi', 'PQ Index (WPI)'),
            
            # ISO4406颗粒数
            (r'particle.*count.*iso4406.*颗粒数', 'Particle Count ISO4406'),
            (r'iso4406.*颗粒数', 'Particle Count ISO4406'),
            (r'颗粒数.*iso4406', 'Particle Count ISO4406'),
            
            # 总酸值
            (r'tan.*mg.*koh.*总酸值', 'TAN'),
            (r'总酸值', 'TAN'),
            
            # 水分
            (r'water.*content.*水分', 'Water Content'),
            (r'水分', 'Water Content'),
            
            # 金属元素 (格式: XX ppm/元素名)
            (r'ag.*ppm.*银', 'Ag ppm / 银'),
            (r'al.*ppm.*铝', 'Al ppm / 铝'),
            (r'b.*ppm.*硼', 'B ppm / 硼'),
            (r'ba.*ppm.*钡', 'Ba ppm / 钡'),
            (r'ca.*ppm.*钙', 'Ca ppm / 钙'),
            (r'cr.*ppm.*铬', 'Cr ppm / 铬'),
            (r'cu.*ppm.*铜', 'Cu ppm / 铜'),
            (r'fe.*ppm.*铁', 'Fe ppm / 铁'),
            (r'k.*ppm.*钾', 'K ppm / 钾'),
            (r'mg.*ppm.*镁', 'Mg ppm / 镁'),
            (r'mo.*ppm.*钼', 'Mo ppm / 钼'),
            (r'na.*ppm.*钠', 'Na ppm / 钠'),
            (r'ni.*ppm.*镍', 'Ni ppm / 镍'),
            (r'p.*ppm.*磷', 'P ppm / 磷'),
            (r'pb.*ppm.*铅', 'Pb ppm / 铅'),
            (r'si.*ppm.*硅', 'Si ppm / 硅'),
            (r'sn.*ppm.*锡', 'Sn ppm / 锡'),
            (r'ti.*ppm.*钛', 'Ti ppm / 钛'),
            (r'v.*ppm.*钒', 'V ppm / 钒'),
            (r'zn.*ppm.*锌', 'Zn ppm / 锌'),
        ]
        
        for pattern, standard_name in keyword_mappings:
            if re.search(pattern, name):
                return standard_name
        
        # 如果没有匹配到，返回清理后的原名称
        return name
    
    for param in parameters:
        param_name = normalize_param_name(param.parameter_name)
        report_date = param.report.report_date.strftime('%Y-%m-%d')
        
        if param_name not in param_data:
            param_data[param_name] = {
                'parameter_name': param_name,
                'unit': param.unit,
                'standard_range': param.standard_range or '',
                'category': classify_parameter_category(param_name),
                'values': {},  # key: date, value: {'value': xxx, 'is_normal': True/False}
            }
        
        param_data[param_name]['values'][report_date] = {
            'value': param.parameter_value,
            'is_normal': param.is_normal
        }
    
    # 构建表格数据 - 每行一个指标，每列一个日期
    table_data = []
    date_list = [d.strftime('%Y-%m-%d') for d in report_dates]
    
    for param_name, data in param_data.items():
        row = {
            'parameter_name': data['parameter_name'],
            'unit': data['unit'],
            'standard_range': data['standard_range'],
            'category': data['category'],
        }
        
        # 添加每个日期的值
        values_list = []
        for date in date_list:
            if date in data['values']:
                row[f'value_{date}'] = data['values'][date]['value']
                row[f'normal_{date}'] = data['values'][date]['is_normal']
                values_list.append(data['values'][date]['value'])
            else:
                row[f'value_{date}'] = None
                row[f'normal_{date}'] = None
                values_list.append(None)
        
        # 计算趋势（最近两次的比较）
        valid_values = [v for v in values_list if v is not None]
        if len(valid_values) >= 2:
            latest = valid_values[0]
            previous = valid_values[1]
            if latest > previous:
                row['trend'] = '↑ 上升'
                row['trend_class'] = 'trend-up'
            elif latest < previous:
                row['trend'] = '↓ 下降'
                row['trend_class'] = 'trend-down'
            else:
                row['trend'] = '→ 持平'
                row['trend_class'] = 'trend-flat'
        else:
            row['trend'] = '-'
            row['trend_class'] = ''
        
        table_data.append(row)
    
    # 定义列名
    columns = ['parameter_name', 'unit', 'standard_range', 'category'] + [f'value_{d}' for d in date_list] + ['trend']
    
    return JsonResponse({
        'data': table_data, 
        'columns': columns,
        'dates': date_list
    })

def classify_parameter_category(parameter_name):
    """参数分类函数"""
    name = parameter_name.lower()
    
    # 水分相关参数
    if '水' in name or 'water' in name or 'moisture' in name:
        return '水分'
    
    # 粘度相关参数
    if '粘度' in name or 'viscosity' in name or '粘度指数' in name:
        return '粘度'
    
    # 金属元素相关参数
    metal_elements = ['铁', '铜', '铝', '硅', '钠', '钒', '镍', '铬', '锰', '镁', '钙', '锌', '铅', '锡', '银', '金', '铂', '钛', '钴', '钼', '钨', '锑', '砷', '汞', '镉', '铍', '锂', '钾', '锶', '钡', '铋', '铈', '镧', '钕', '钇', '钪', '锆', '铪', '钽', '铌', '铼', '锝', '钫', '镭', '锕', '钍', '铀', '钚', 'iron', 'copper', 'aluminum', 'silicon', 'sodium', 'vanadium', 'nickel', 'chromium', 'manganese', 'magnesium', 'calcium', 'zinc', 'lead', 'tin', 'silver', 'gold', 'platinum', 'titanium', 'cobalt', 'molybdenum', 'tungsten', 'antimony', 'arsenic', 'mercury', 'cadmium', 'beryllium', 'lithium', 'potassium', 'strontium', 'barium', 'bismuth', 'cerium', 'lanthanum', 'neodymium', 'yttrium', 'scandium', 'zirconium', 'hafnium', 'tantalum', 'niobium', 'rhenium', 'technetium', 'francium', 'radium', 'actinium', 'thorium', 'uranium', 'plutonium']
    
    if any(metal in name for metal in metal_elements):
        return '金属'
    
    # 其他参数归类到其他
    return '其他'

def export_data(request):
    """导出数据"""
    equipment_id = request.GET.get('equipment_id')
    parameter_name = request.GET.get('parameter_name')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # 构建查询条件
    queryset = OilParameter.objects.all()
    
    if equipment_id:
        queryset = queryset.filter(report__equipment_id=equipment_id)
    
    if parameter_name:
        queryset = queryset.filter(parameter_name=parameter_name)
    
    if start_date:
        queryset = queryset.filter(report__report_date__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(report__report_date__lte=end_date)
    
    queryset = queryset.order_by('report__report_date')
    
    # 创建Excel文件
    data = []
    for param in queryset:
        data.append({
            '景点': param.report.equipment.attraction.name,
            '设备': param.report.equipment.name,
            '位置': param.report.equipment.location,
            '设备类型': param.report.equipment.equipment_type,
            '报告日期': param.report.report_date.strftime('%Y-%m-%d') if param.report.report_date else '',
            '采样日期': param.report.sample_date.strftime('%Y-%m-%d') if param.report.sample_date else '',
            '报告编号': param.report.report_number or '',
            '参数名称': param.parameter_name,
            '参数值': param.parameter_value,
            '单位': param.unit,
            '标准范围': param.standard_range or '',
            '是否正常': '是' if param.is_normal else '否'
        })
    
    # 如果没有数据，创建空表格但包含表头
    if not data:
        data = [{
            '景点': '',
            '设备': '',
            '位置': '',
            '设备类型': '',
            '报告日期': '',
            '采样日期': '',
            '报告编号': '',
            '参数名称': '',
            '参数值': '',
            '单位': '',
            '标准范围': '',
            '是否正常': ''
        }]
    
    df = pd.DataFrame(data)
    
    # 生成Excel文件
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f'oil_inspection_data_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # 使用BytesIO创建内存中的Excel文件
    from io import BytesIO
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='油品检测数据')
        
        # 获取工作表对象，设置列宽
        worksheet = writer.sheets['油品检测数据']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    response.write(output.getvalue())
    
    return response

def confirm_upload(request):
    """确认上传OCR预览数据到数据库 - 支持重复数据检测"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '请使用POST方法'})
    
    try:
        # 获取OCR数据
        ocr_data = request.session.get('ocr_preview')
        if not ocr_data:
            return JsonResponse({'success': False, 'error': 'OCR预览数据已过期，请重新上传文件'})
        
        # 创建虚拟的UploadedFile对象（因为实际文件已经处理过了）
        from django.core.files.base import ContentFile
        from io import BytesIO
        
        # 创建一个虚拟的PDF文件
        dummy_content = b"PDF content"
        uploaded_file = UploadedFile.objects.create(
            file=ContentFile(dummy_content, name=ocr_data['filename']),
            original_filename=ocr_data['filename'],
            file_type='pdf',
            file_size=len(dummy_content),
            processing_status='pending'
        )
        
        # 获取用户选择的设备ID（必须）
        selected_equipment_id = request.POST.get('selected_equipment')
        
        if not selected_equipment_id:
            return JsonResponse({'success': False, 'error': '请选择景点和设备后再确认上传！'})
        
        # 用户手动选择了设备
        try:
            equipment = Equipment.objects.get(id=selected_equipment_id)
            print(f"用户选择设备: {equipment.name}")
        except Equipment.DoesNotExist:
            return JsonResponse({'success': False, 'error': '选择的设备不存在'})
        
        # 获取MD内容
        md_content = ocr_data.get('md_content', '')
        
        # 处理多次测量数据
        multi_data = ocr_data.get('multi_data', {})
        has_multiple_measurements = ocr_data.get('has_multiple_measurements', False)
        
        # 重复数据检测和处理
        duplicate_info = {
            'existing_dates': [],
            'new_dates': [],
            'skipped_count': 0,
            'created_count': 0
        }
        
        if has_multiple_measurements and multi_data:
            # 多次测量情况 - 检查每个采样日期
            try:
                from enhanced_multi_measurement_extraction import create_multiple_reports_enhanced
                
                # 重建多次测量数据结构
                reconstructed_multi_data = {
                    'sample_dates': multi_data.get('sample_dates', []),
                    'measurements': multi_data.get('measurements', [])
                }
                
                # 转换日期字符串为日期对象
                sample_dates = []
                for date_str in reconstructed_multi_data.get('sample_dates', []):
                    if isinstance(date_str, str):
                        try:
                            sample_dates.append(datetime.strptime(date_str, '%Y-%m-%d').date())
                        except ValueError:
                            # 尝试其他日期格式
                            try:
                                sample_dates.append(datetime.fromisoformat(date_str.replace('Z', '+00:00')).date())
                            except ValueError:
                                print(f"无法解析日期: {date_str}")
                                continue
                    else:
                        sample_dates.append(date_str)
                
                # 检查重复的采样日期
                existing_reports = OilInspectionReport.objects.filter(
                    equipment=equipment,
                    sample_date__in=sample_dates
                ).values_list('sample_date', flat=True)
                
                existing_dates_set = set(existing_reports)
                new_dates = [date for date in sample_dates if date not in existing_dates_set]
                duplicate_dates = [date for date in sample_dates if date in existing_dates_set]
                
                duplicate_info['existing_dates'] = [date.strftime('%Y-%m-%d') for date in duplicate_dates]
                duplicate_info['new_dates'] = [date.strftime('%Y-%m-%d') for date in new_dates]
                duplicate_info['skipped_count'] = len(duplicate_dates)
                
                if new_dates:
                    # 只为新的采样日期创建报告
                    # 过滤出新的采样日期的数据
                    filtered_multi_data = {
                        'sample_dates': new_dates,
                        'measurements': reconstructed_multi_data.get('measurements', [])
                    }
                    
                    reports_data = create_multiple_reports_enhanced(filtered_multi_data, equipment, '')

                    # 确保reports_data是可迭代的列表
                    if not isinstance(reports_data, (list, tuple)):
                        print(f"警告：create_multiple_reports_enhanced返回了非列表类型：{type(reports_data)}，值为：{reports_data}")
                        reports_data = []

                    created_reports = []
                    for report_data in reports_data:
                        # 创建油品检测报告
                        report = OilInspectionReport.objects.create(
                            equipment=equipment,
                            report_date=report_data['report_date'],
                            sample_date=report_data['sample_date'],
                            report_number=report_data['report_number'],
                            pdf_file=uploaded_file.file,
                            md_content=md_content,
                            is_processed=True
                        )
                        
                        # 保存油品参数（添加安全检查）
                        saved_param_count = 0
                        parameters_list = report_data.get('parameters', [])
                        if not isinstance(parameters_list, (list, tuple)):
                            print(f"警告：报告数据中的parameters不是列表类型：{type(parameters_list)}")
                            parameters_list = []

                        for param_data in parameters_list:
                            if isinstance(param_data, dict) and 'parameter_name' in param_data and 'parameter_value' in param_data:
                                try:
                                    OilParameter.objects.create(
                                        report=report,
                                        parameter_name=param_data['parameter_name'],
                                        parameter_value=param_data['parameter_value'],
                                        unit=param_data.get('unit', ''),
                                        standard_range=param_data.get('standard_range', ''),
                                        is_normal=param_data.get('is_normal', True)
                                    )
                                    saved_param_count += 1
                                except Exception as e:
                                    print(f"保存多次测量参数失败：{param_data}，错误：{e}")
                            else:
                                print(f"警告：跳过无效的多次测量参数数据：{param_data}")

                        print(f"报告 {report.id} 成功保存了 {saved_param_count} 个参数")
                        
                        created_reports.append(report)
                    
                    duplicate_info['created_count'] = len(created_reports)
                    print(f"成功创建 {len(created_reports)} 个新报告，跳过 {len(duplicate_dates)} 个重复日期")
                else:
                    print(f"所有采样日期都已存在，跳过创建")
                
            except ImportError:
                # 如果多次测量处理不可用，使用单次测量
                duplicate_info = handle_single_upload_duplicate_check(uploaded_file, md_content, equipment, duplicate_info)
        else:
            # 单次测量情况 - 检查采样日期
            duplicate_info = handle_single_upload_duplicate_check(uploaded_file, md_content, equipment, duplicate_info)
        
        # 更新上传文件状态
        uploaded_file.processed = True
        uploaded_file.processing_status = 'completed'
        uploaded_file.save()
        
        # 清理session数据
        if 'ocr_preview' in request.session:
            del request.session['ocr_preview']
        
        # 构建返回消息
        if duplicate_info['skipped_count'] > 0 and duplicate_info['created_count'] > 0:
            message = f'数据保存成功！创建了{duplicate_info["created_count"]}个新报告，跳过了{duplicate_info["skipped_count"]}个已存在的采样日期数据。'
        elif duplicate_info['skipped_count'] > 0 and duplicate_info['created_count'] == 0:
            message = f'所有采样日期的数据都已存在，未创建新报告。跳过了{duplicate_info["skipped_count"]}个重复数据。'
        else:
            total_params = OilParameter.objects.filter(report__pdf_file=uploaded_file.file).count()
            message = f'数据保存成功！创建了{duplicate_info["created_count"]}个报告，解析了{total_params}个参数。'
        
        # 返回成功响应
        return JsonResponse({
            'success': True,
            'message': message,
            'duplicate_info': duplicate_info,
            'report_number': '',
            'redirect_url': reverse('oil_records:dashboard')
        })
        
    except Exception as e:
        print(f"确认上传失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'保存失败：{str(e)}'
        })

def handle_single_upload_duplicate_check(uploaded_file, md_content, equipment, duplicate_info):
    """处理单次上传的重复数据检测"""
    # 解析MD内容提取油品参数
    parameters = parse_oil_parameters(md_content)

    # 确保parameters是可迭代的列表
    if not isinstance(parameters, (list, tuple)):
        print(f"警告：parse_oil_parameters返回了非列表类型：{type(parameters)}，值为：{parameters}")
        parameters = []

    # 尝试从MD内容中提取采样日期
    sample_date = extract_sample_date_from_md(md_content)
    if not sample_date:
        sample_date = timezone.now().date()

    # 检查是否已存在相同设备和采样日期的报告
    existing_report = OilInspectionReport.objects.filter(
        equipment=equipment,
        sample_date=sample_date
    ).first()

    if existing_report:
        duplicate_info['existing_dates'] = [sample_date.strftime('%Y-%m-%d')]
        duplicate_info['skipped_count'] = 1
        print(f"跳过重复数据：设备 {equipment.name} 在 {sample_date} 的数据已存在")
    else:
        # 创建新的油品检测报告
        report = OilInspectionReport.objects.create(
            equipment=equipment,
            report_date=timezone.now().date(),
            sample_date=sample_date,
            report_number='',
            pdf_file=uploaded_file.file,
            md_content=md_content,
            is_processed=True
        )

        # 保存油品参数（添加额外的安全检查）
        saved_param_count = 0
        for param in parameters:
            if isinstance(param, dict) and 'name' in param and 'value' in param:
                try:
                    OilParameter.objects.create(
                        report=report,
                        parameter_name=param['name'],
                        parameter_value=param['value'],
                        unit=param.get('unit', ''),
                        standard_range=param.get('standard_range', ''),
                        is_normal=param.get('is_normal', True)
                    )
                    saved_param_count += 1
                except Exception as e:
                    print(f"保存参数失败：{param}，错误：{e}")
            else:
                print(f"警告：跳过无效的参数数据：{param}")

        print(f"成功保存了 {saved_param_count} 个参数")

        duplicate_info['new_dates'] = [sample_date.strftime('%Y-%m-%d')]
        duplicate_info['created_count'] = 1
        print(f"成功创建单个报告：设备 {equipment.name} 采样日期 {sample_date}")

    return duplicate_info

def extract_sample_date_from_md(md_content):
    """从MD内容中提取采样日期"""
    import re
    from datetime import datetime
    
    # 常见的日期模式
    date_patterns = [
        r'采样日期[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'取样日期[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'Sample\s*Date[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*采样',
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*取样'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, md_content, re.IGNORECASE | re.MULTILINE)
        if matches:
            try:
                # 尝试解析日期
                date_str = matches[0].replace('/', '-')
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                continue
    
    return None

def download_md_file(request, report_id):
    """下载MD文件"""
    report = get_object_or_404(OilInspectionReport, id=report_id)
    
    if not report.md_content:
        return JsonResponse({'error': '该报告没有MD内容'}, status=404)
    
    # 创建MD文件响应
    response = HttpResponse(report.md_content, content_type='text/markdown')
    filename = f"{report.equipment.name}_{report.report_date}.md"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@require_http_methods(["GET"])
def get_attractions_and_equipment_api(request):
    """获取所有景点和设备数据API"""
    try:
        # 获取所有景点
        attractions = Attraction.objects.all().order_by('name')
        attractions_data = []
        for attraction in attractions:
            attractions_data.append({
                'id': attraction.id,
                'name': attraction.name,
                'description': attraction.description
            })
        
        # 获取所有设备，按景点分组
        equipment_data = {}
        for attraction in attractions:
            equipment_list = Equipment.objects.filter(attraction=attraction).order_by('name')
            equipment_data[str(attraction.id)] = []
            for equipment in equipment_list:
                equipment_data[str(attraction.id)].append({
                    'id': equipment.id,
                    'name': equipment.name,
                    'location': equipment.location,
                    'equipment_type': equipment.equipment_type,
                    'display_name': f"{equipment.name} - {equipment.location}"
                })
        
        return JsonResponse({
            'success': True,
            'attractions': attractions_data,
            'equipment': equipment_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'获取数据失败：{str(e)}'
        }, status=500)


def downtime_report(request):
    """停机报告页面"""
    return render(request, 'oil_records/downtime_report.html')


def generate_downtime_report_view(request):
    """生成停机报告API"""
    if request.method == 'POST':
        try:
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')

            if not start_date or not end_date:
                return JsonResponse({
                    'success': False,
                    'error': '请提供开始日期和结束日期'
                }, status=400)

            # 导入 downtime_analyzer 模块
            from .downtime_analyzer import generate_downtime_report

            # 生成报告（返回3个HTML）
            reports = generate_downtime_report(start_date, end_date)

            return JsonResponse({
                'success': True,
                'chart_html': reports['chart'],
                'detail_101_html': reports['detail_101'],
                'detail_105_html': reports['detail_105']
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'生成报告失败：{str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': '仅支持POST请求'
    }, status=405)
