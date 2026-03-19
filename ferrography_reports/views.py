from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.db.models import Q
from oil_records.models import Attraction, Equipment
from .models import FerrographyReport, FerrographyParticle, FerrographyDiagnosis, FerrographyAttraction, FerrographyEquipment
import json
import requests
import uuid
import queue
import threading
from datetime import datetime
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

# 批量上传任务队列
batch_upload_tasks = {}


def ferrography_home(request):
    """铁谱分析首页"""
    report_count = FerrographyReport.objects.count()
    recent_reports = FerrographyReport.objects.select_related('equipment__attraction').order_by('-created_at')[:10]
    
    context = {
        'report_count': report_count,
        'recent_reports': recent_reports,
    }
    return render(request, 'ferrography_reports/home.html', context)


def upload_ferrography_report(request):
    """上传铁谱报告"""
    if request.method == 'POST':
        if 'pdf_file' in request.FILES:
            pdf_file = request.FILES['pdf_file']
            
            # 检查是否是预览请求
            action = request.POST.get('action', '')
            
            if action == 'preview':
                return preview_ferrography_data(request, pdf_file)
            elif action == 'confirm':
                return confirm_ferrography_upload(request)
            else:
                # 默认跳转到预览
                return preview_ferrography_data(request, pdf_file)
        else:
            messages.error(request, '请选择要上传的PDF文件')
    
    # GET请求时显示上传页面
    attractions = Attraction.objects.all().order_by('name')
    return render(request, 'ferrography_reports/upload.html', {'attractions': attractions})


def preview_ferrography_data(request, pdf_file):
    """预览铁谱报告数据"""
    try:
        # 重置文件指针
        pdf_file.seek(0)
        
        # 调用OCR处理
        print(f"开始处理铁谱报告: {pdf_file.name}")
        md_content = call_mineru_api(pdf_file)
        print(f"OCR处理完成，MD内容长度: {len(md_content)}")
        
        # 提取铁谱报告信息（使用新的数据提取模块）
        from .ferrography_data_extraction import extract_ferrography_data_from_md
        from .ferrography_extraction import match_equipment_for_ferrography
        
        ferrography_data = extract_ferrography_data_from_md(md_content)
        print(f"📊 提取到的铁谱数据: {json.dumps(ferrography_data, ensure_ascii=False, indent=2)}")
        
        # 匹配设备
        print(f"🔍 开始匹配设备，文件名: {pdf_file.name}")
        matched_info = match_equipment_for_ferrography({'equipment_name': '', 'equipment_location': ''}, pdf_file.name)
        print(f"📊 匹配结果: {matched_info}")
        
        # 存储到session
        matched_equipment = matched_info.get('matched_equipment')
        matched_attraction = matched_info.get('matched_attraction')
        
        session_data = {
            'filename': pdf_file.name,
            'md_content': md_content,
            'ferrography_info': ferrography_data,
            'matched_info': {
                'equipment_id': matched_info.get('matched_equipment_id'),
                'equipment_name': matched_equipment.name if matched_equipment else None,
                'attraction_name': matched_attraction.name if matched_attraction else None,
            },
        }
        print(f"📊 Session数据: {session_data}")
        
        request.session['ferrography_preview'] = session_data
        
        # 返回JSON响应
        return JsonResponse({
            'success': True,
            'redirect': reverse('ferrography_reports:preview_display'),
            'message': '铁谱报告处理完成，正在跳转到预览页面'
        })
        
    except Exception as e:
        print(f"铁谱报告预览处理失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'处理失败：{str(e)}'
        })


def preview_display(request):
    """显示铁谱报告预览"""
    preview_data = request.session.get('ferrography_preview')
    
    if not preview_data:
        messages.error(request, '没有预览数据，请重新上传')
        return redirect('ferrography_reports:upload')
    
    # 获取所有景点和设备供用户选择（使用铁谱检测自己的表）
    attractions = FerrographyAttraction.objects.all().order_by('name')
    
    # 获取匹配的设备信息
    matched_equipment_id = preview_data.get('matched_info', {}).get('equipment_id')
    matched_equipment = None
    if matched_equipment_id:
        matched_equipment = FerrographyEquipment.objects.filter(id=matched_equipment_id).first()
    
    context = {
        'preview_data': preview_data,
        'attractions': attractions,
        'matched_equipment': matched_equipment,
    }
    return render(request, 'ferrography_reports/preview.html', context)


def confirm_ferrography_upload(request):
    """确认上传铁谱报告"""
    if request.method != 'POST':
        messages.error(request, '请使用POST方法提交数据')
        return redirect('ferrography_reports:upload')
    
    preview_data = request.session.get('ferrography_preview')
    if not preview_data:
        messages.error(request, '会话已过期，请重新上传')
        return redirect('ferrography_reports:upload')
    
    try:
        # 获取用户确认的设备（使用铁谱检测自己的设备表）
        confirmed_equipment_id = request.POST.get('confirmed_equipment')
        if confirmed_equipment_id:
            equipment = get_object_or_404(FerrographyEquipment, id=confirmed_equipment_id)
        else:
            # 使用自动匹配的设备
            matched_equipment_id = preview_data.get('matched_info', {}).get('equipment_id')
            if matched_equipment_id:
                equipment = get_object_or_404(FerrographyEquipment, id=matched_equipment_id)
            else:
                messages.error(request, '请选择设备')
                return redirect('ferrography_reports:preview_display')
        
        # 获取报告日期和采样日期
        report_date_str = request.POST.get('report_date')
        sample_date_str = request.POST.get('sample_date')
        
        report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date() if report_date_str else datetime.now().date()
        sample_date = datetime.strptime(sample_date_str, '%Y-%m-%d').date() if sample_date_str else report_date
        
        # 检查是否已存在相同设备和采样日期的报告
        existing_report = FerrographyReport.objects.filter(
            equipment=equipment,
            sample_date=sample_date
        ).first()
        
        if existing_report:
            messages.warning(request, f'该设备在 {sample_date} 已有铁谱报告（报告编号: {existing_report.report_number}），已跳过保存')
            return redirect('ferrography_reports:home')
        
        # 创建铁谱报告记录
        ferrography_info = preview_data.get('ferrography_info', {})
        
        report = FerrographyReport.objects.create(
            equipment=equipment,
            report_date=report_date,
            sample_date=sample_date,
            report_number=ferrography_info.get('report_number', ''),
            pdf_file=preview_data['filename'],  # 这里需要实际保存文件
            md_content=preview_data.get('md_content', ''),
            processed_data=ferrography_info,
            is_processed=True,
        )
        
        # 保存颗粒信息（使用新提取的完整数据）
        particles = ferrography_info.get('particles', [])
        for particle_data in particles:
            FerrographyParticle.objects.create(
                report=report,
                particle_type=particle_data.get('particle_type', ''),
                concentration=particle_data.get('concentration', ''),
                size_range=particle_data.get('size_range', ''),
                morphology=particle_data.get('morphology', ''),
                wear_mechanism=particle_data.get('wear_mechanism', ''),
                severity_level=particle_data.get('severity_level', ''),
            )
        
        # 保存诊断信息（使用新提取的完整数据）
        diagnosis_data = ferrography_info.get('diagnosis', {})
        if diagnosis_data and isinstance(diagnosis_data, dict):
            FerrographyDiagnosis.objects.create(
                report=report,
                overall_assessment=diagnosis_data.get('overall_assessment', ''),
                wear_status=diagnosis_data.get('wear_status', ''),
                recommendations=diagnosis_data.get('recommendations', ''),
            )
        elif diagnosis_data and isinstance(diagnosis_data, str):
            # 兼容旧格式
            FerrographyDiagnosis.objects.create(
                report=report,
                overall_assessment=diagnosis_data,
            )
        
        messages.success(request, f'铁谱报告上传成功！')
        return redirect('ferrography_reports:home')
        
    except Exception as e:
        print(f"铁谱报告上传失败: {e}")
        messages.error(request, f'上传失败：{str(e)}')
        return redirect('ferrography_reports:preview_display')


def report_detail(request, report_id):
    """查看铁谱报告详情"""
    report = get_object_or_404(FerrographyReport.objects.select_related('equipment__attraction'), id=report_id)
    particles = FerrographyParticle.objects.filter(report=report)
    diagnosis = FerrographyDiagnosis.objects.filter(report=report).first()
    
    context = {
        'report': report,
        'particles': particles,
        'diagnosis': diagnosis,
    }
    return render(request, 'ferrography_reports/detail.html', context)


def report_list(request):
    """铁谱报告列表"""
    reports = FerrographyReport.objects.select_related('equipment__attraction').order_by('-report_date')
    
    # 筛选
    attraction_id = request.GET.get('attraction')
    if attraction_id:
        reports = reports.filter(equipment__attraction_id=attraction_id)
    
    equipment_id = request.GET.get('equipment')
    if equipment_id:
        reports = reports.filter(equipment_id=equipment_id)
    
    context = {
        'reports': reports,
        'attractions': FerrographyAttraction.objects.all().order_by('name'),
    }
    return render(request, 'ferrography_reports/list.html', context)


def call_mineru_api(pdf_file):
    """调用mineru-api进行OCR处理"""
    from django.conf import settings
    import os
    from io import BytesIO
    
    # 使用settings.py中配置的API地址
    api_url = settings.MINERU_API_URL
    
    # 重置文件指针到开始位置
    pdf_file.seek(0)
    
    # 读取文件内容
    file_content = pdf_file.read()
    
    # 重新创建文件对象以确保正确格式
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


# API接口
def get_equipment_api(request):
    """获取设备列表API"""
    attraction_id = request.GET.get('attraction_id')
    
    if attraction_id:
        equipments = Equipment.objects.filter(attraction_id=attraction_id).order_by('name')
    else:
        equipments = Equipment.objects.all().order_by('name')
    
    equipment_list = []
    for eq in equipments:
        equipment_list.append({
            'id': eq.id,
            'name': eq.name,
            'location': eq.location,
            'equipment_type': eq.equipment_type,
        })
    
    return JsonResponse({'equipment': equipment_list})


@csrf_exempt
def batch_upload(request):
    """批量上传铁谱报告"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '请使用POST方法'})
    
    if 'pdf_files' not in request.FILES:
        return JsonResponse({'success': False, 'error': '请选择要上传的PDF文件'})
    
    pdf_files = request.FILES.getlist('pdf_files')
    if not pdf_files:
        return JsonResponse({'success': False, 'error': '没有有效的PDF文件'})
    
    results = []
    success_count = 0
    error_count = 0
    
    from .ferrography_extraction import match_ferrography_equipment, extract_ferrography_data
    
    for i, pdf_file in enumerate(pdf_files):
        file_result = {
            'filename': pdf_file.name,
            'status': 'pending',
            'message': '',
            'equipment_name': '',
            'attraction_name': '',
            'error': ''
        }
        
        try:
            print(f"\n处理文件 {i+1}/{len(pdf_files)}: {pdf_file.name}")
            
            # 检查文件大小
            if pdf_file.size > 50 * 1024 * 1024:
                raise ValueError(f"文件太大: {pdf_file.size / 1024 / 1024:.1f}MB")
            
            # OCR处理
            pdf_file.seek(0)
            md_content = call_mineru_api(pdf_file)
            print(f"OCR完成，内容长度: {len(md_content)}")
            
            # 匹配设备
            matched_info = match_ferrography_equipment(pdf_file.name)
            print(f"匹配结果: {matched_info}")
            
            file_result['equipment_name'] = matched_info.get('matched_equipment_name', '')
            file_result['attraction_name'] = matched_info.get('matched_attraction_name', '')
            
            if matched_info.get('matched_equipment_id'):
                file_result['status'] = 'success'
                file_result['message'] = f"匹配到设备: {matched_info['matched_equipment_name']}"
                success_count += 1
            elif matched_info.get('matched_attraction_id'):
                file_result['status'] = 'partial'
                file_result['message'] = f"匹配到景点: {matched_info['matched_attraction_name']}，设备需手动选择"
                success_count += 1
            else:
                file_result['status'] = 'failed'
                file_result['message'] = '未能自动识别景点和设备'
                error_count += 1
            
        except Exception as e:
            print(f"处理失败: {e}")
            file_result['status'] = 'error'
            file_result['message'] = f'处理失败: {str(e)}'
            file_result['error'] = str(e)
            error_count += 1
        
        results.append(file_result)
    
    return JsonResponse({
        'success': True,
        'total': len(pdf_files),
        'success_count': success_count,
        'error_count': error_count,
        'results': results
    })


# ========== SSE流式批量上传 ==========

def batch_upload_stream(request):
    """SSE 流式批量上传 - 实时推送每个文件的处理状态"""
    task_id = request.GET.get('task_id')
    print(f"铁谱SSE连接请求: task_id={task_id}")
    
    if not task_id or task_id not in batch_upload_tasks:
        print(f"无效的任务ID: {task_id}")
        return JsonResponse({'success': False, 'error': '无效的任务ID'})
    
    task_queue = batch_upload_tasks[task_id]
    print(f"铁谱SSE连接已建立: task_id={task_id}")
    
    def event_stream():
        """生成 SSE 事件流"""
        while True:
            try:
                message = task_queue.get(timeout=1)
                print(f"铁谱SSE发送: {message.get('type')} - {message.get('filename', 'N/A')}")
                
                yield f"data: {json.dumps(message)}\n\n"
                
                if message.get('type') in ['complete', 'error']:
                    break
                    
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                continue
            except Exception as e:
                print(f"铁谱SSE错误: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
        
        if task_id in batch_upload_tasks:
            del batch_upload_tasks[task_id]
            print(f"铁谱任务已清理: {task_id}")
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@csrf_exempt
def batch_upload_async(request):
    """启动异步批量上传任务"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支持POST请求'})
    
    if 'pdf_files' not in request.FILES:
        return JsonResponse({'success': False, 'error': '请选择要上传的PDF文件'})
    
    pdf_files = request.FILES.getlist('pdf_files')
    if not pdf_files:
        return JsonResponse({'success': False, 'error': '没有有效的PDF文件'})
    
    task_id = str(uuid.uuid4())
    task_queue = queue.Queue()
    batch_upload_tasks[task_id] = task_queue
    
    # 读取文件内容到内存
    file_data_list = []
    for pdf_file in pdf_files:
        file_data_list.append({
            'name': pdf_file.name,
            'content': pdf_file.read(),
            'size': pdf_file.size
        })
    
    def process_files():
        """后台处理文件"""
        from .ferrography_extraction import match_ferrography_equipment, extract_ferrography_data
        
        try:
            task_queue.put({
                'type': 'start',
                'total': len(file_data_list),
                'message': f'开始处理 {len(file_data_list)} 个文件'
            })
            
            for i, file_data in enumerate(file_data_list):
                task_queue.put({
                    'type': 'processing',
                    'index': i,
                    'filename': file_data['name'],
                    'progress': f'{i+1}/{len(file_data_list)}',
                    'message': f'正在处理: {file_data["name"]}'
                })
                
                try:
                    # 创建内存文件对象
                    pdf_file = InMemoryUploadedFile(
                        file=BytesIO(file_data['content']),
                        field_name='pdf_files',
                        name=file_data['name'],
                        content_type='application/pdf',
                        size=file_data['size'],
                        charset=None
                    )
                    
                    # OCR处理
                    pdf_file.seek(0)
                    md_content = call_mineru_api(pdf_file)
                    
                    # 匹配设备
                    matched_info = match_ferrography_equipment(file_data['name'])
                    print(f"匹配结果: {matched_info}")
                    
                    # 只有当匹配到设备时才保存报告
                    if matched_info.get('matched_equipment_id'):
                        try:
                            # 使用新的数据提取函数
                            from .ferrography_data_extraction import extract_ferrography_data_from_md
                            extracted_data = extract_ferrography_data_from_md(md_content)
                            
                            # 获取设备（使用铁谱检测自己的设备表）
                            equipment_id = matched_info['matched_equipment_id']
                            print(f"查询设备ID: {equipment_id}")
                            
                            try:
                                equipment = FerrographyEquipment.objects.get(id=equipment_id)
                            except FerrographyEquipment.DoesNotExist:
                                print(f"❌ 设备ID {equipment_id} 不存在于数据库")
                                # 尝试查找所有可用设备
                                all_equipments = list(FerrographyEquipment.objects.filter(
                                    name__contains='BB'
                                ).values('id', 'name'))
                                print(f"可用BB设备: {all_equipments}")
                                raise
                            
                            # 保存PDF文件
                            pdf_file.seek(0)
                            from django.core.files.base import ContentFile
                            from .models import FerrographyReport, FerrographyParticle, FerrographyDiagnosis
                            
                            # 解析日期
                            sample_date = datetime.now().date()
                            report_date = datetime.now().date()
                            if extracted_data.get('report_date'):
                                try:
                                    report_date = datetime.strptime(extracted_data['report_date'], '%Y-%m-%d').date()
                                except:
                                    pass
                            if extracted_data.get('sample_date'):
                                try:
                                    sample_date = datetime.strptime(extracted_data['sample_date'], '%Y-%m-%d').date()
                                except:
                                    pass
                            
                            # 检查是否已存在相同设备和采样日期的报告
                            existing_report = FerrographyReport.objects.filter(
                                equipment=equipment,
                                sample_date=sample_date
                            ).first()
                            
                            if existing_report:
                                status = 'skipped'
                                message = f"跳过：该设备在 {sample_date} 已有报告（编号: {existing_report.report_number}）"
                                task_queue.put({
                                    'type': 'file_complete',
                                    'index': i,
                                    'filename': file_data['name'],
                                    'status': status,
                                    'message': message,
                                    'equipment_name': matched_info.get('matched_equipment_name', ''),
                                    'attraction_name': matched_info.get('matched_attraction_name', '')
                                })
                                continue
                            
                            # 创建报告
                            report = FerrographyReport.objects.create(
                                equipment=equipment,
                                report_number=f"FG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                                sample_date=sample_date,
                                report_date=report_date,
                                pdf_file=ContentFile(file_data['content'], name=file_data['name']),
                                md_content=md_content,
                                processed_data=extracted_data,
                                is_processed=True,
                            )
                            
                            # 保存颗粒信息（使用正确的字段名）
                            particles = extracted_data.get('particles', [])
                            for particle_data in particles:
                                FerrographyParticle.objects.create(
                                    report=report,
                                    particle_type=particle_data.get('particle_type', ''),
                                    concentration=particle_data.get('concentration', ''),
                                    size_range=particle_data.get('size_range', ''),
                                    morphology=particle_data.get('morphology', ''),
                                    wear_mechanism=particle_data.get('wear_mechanism', ''),
                                    severity_level=particle_data.get('severity_level', ''),
                                )
                            
                            # 保存诊断信息
                            diagnosis_data = extracted_data.get('diagnosis', {})
                            if diagnosis_data and isinstance(diagnosis_data, dict):
                                FerrographyDiagnosis.objects.create(
                                    report=report,
                                    overall_assessment=diagnosis_data.get('overall_assessment', ''),
                                    wear_status=diagnosis_data.get('wear_status', ''),
                                    recommendations=diagnosis_data.get('recommendations', ''),
                                )
                            
                            status = 'success'
                            message = f"已保存报告: {matched_info['matched_equipment_name']}"
                            
                        except Exception as inner_e:
                            print(f"保存报告失败: {str(inner_e)}")
                            status = 'error'
                            message = f"保存失败: {str(inner_e)}"
                    elif matched_info.get('matched_attraction_id'):
                        status = 'partial'
                        message = f"匹配到景点: {matched_info['matched_attraction_name']}，设备需手动选择"
                    else:
                        status = 'failed'
                        message = '未能自动识别景点和设备'
                    
                    task_queue.put({
                        'type': 'file_complete',
                        'index': i,
                        'filename': file_data['name'],
                        'status': status,
                        'message': message,
                        'equipment_name': matched_info.get('matched_equipment_name', ''),
                        'attraction_name': matched_info.get('matched_attraction_name', '')
                    })
                    
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    print(f"处理文件异常: {str(e)}\n{error_detail}")
                    task_queue.put({
                        'type': 'file_error',
                        'index': i,
                        'filename': file_data['name'],
                        'status': 'error',
                        'message': str(e)
                    })
            
            task_queue.put({
                'type': 'complete',
                'message': '所有文件处理完成'
            })
            
        except Exception as e:
            task_queue.put({
                'type': 'error',
                'message': f'处理过程出错: {str(e)}'
            })
    
    thread = threading.Thread(target=process_files)
    thread.daemon = True
    thread.start()
    
    print(f"铁谱批量上传任务已启动: task_id={task_id}")
    
    return JsonResponse({
        'success': True,
        'task_id': task_id,
        'message': '批量上传任务已启动'
    })
