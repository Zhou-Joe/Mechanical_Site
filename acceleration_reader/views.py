"""
Views for Acceleration Reader application
Handles file upload, data processing, and API endpoints
"""

import json
import os
import numpy as np
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage

from .accdata import AccData, RawData
from .sci_calculation import process_ASTM, process_GB, detect_z_acceleration_reversal, detect_xy_acceleration_reversal, eggXY, eggXZ, eggYZ, coef
from .constants import DEFAULT_CUTOFF_FREQUENCY, MAX_CUTOFF_FREQUENCY, PLOT_COLORS, RESTRAINT_TYPES, CONDITION_TYPES


def home(request):
    """Home page view"""
    context = {
        'default_cutoff': DEFAULT_CUTOFF_FREQUENCY,
        'max_cutoff': MAX_CUTOFF_FREQUENCY,
        'restraint_types': RESTRAINT_TYPES,
        'condition_types': CONDITION_TYPES,
    }
    return render(request, 'acceleration_reader/home.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """Handle file upload and return data info"""
    try:
        uploaded_file = request.FILES.get('file')
        file_type = request.POST.get('file_type', 'standard')  # 'standard' or 'raw'
        cutoff = int(request.POST.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if not uploaded_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        # Save file temporarily
        file_path = default_storage.save(
            os.path.join('acceleration_data', uploaded_file.name),
            uploaded_file
        )
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Process file based on type
        if file_type == 'raw':
            raw_data = RawData(full_path)
            gb_data, astm_data = raw_data.export_data()
            
            # Initialize angle and filter for both
            gb_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0, 
                           seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
            astm_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0, 
                              seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
            
            # Store in session
            if 'accel_data' not in request.session:
                request.session['accel_data'] = {}
            
            request.session['accel_data'][gb_data.filename] = {
                'file_path': file_path,
                'type': 'gb',
            }
            request.session['accel_data'][astm_data.filename] = {
                'file_path': file_path,
                'type': 'astm',
            }
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'files': [
                    {
                        'name': gb_data.filename,
                        'type': 'GB',
                        'stats': gb_data.get_stats_dict('Standard'),
                    },
                    {
                        'name': astm_data.filename,
                        'type': 'ASTM',
                        'stats': astm_data.get_stats_dict('Standard'),
                    }
                ]
            })
        else:
            # Standard acceleration data
            acc_data = AccData(full_path, cutoff=cutoff)
            
            # Store in session
            if 'accel_data' not in request.session:
                request.session['accel_data'] = {}
            
            request.session['accel_data'][acc_data.filename] = {
                'file_path': file_path,
                'type': 'standard',
            }
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'files': [{
                    'name': acc_data.filename,
                    'type': 'Standard',
                    'stats': acc_data.get_stats_dict('Standard'),
                }]
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_plot_data(request):
    """Get plot data for visualization"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        plot_type = data.get('plot_type', 'Standard')  # 'Raw', 'Filter', 'Standard'
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found. Please upload file again.'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Reload and process data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            if file_info['type'] == 'gb':
                acc_data = gb_data
            else:
                acc_data = astm_data
            acc_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0,
                             seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        return JsonResponse({
            'success': True,
            'data': acc_data.to_dict(plot_type),
            'stats': acc_data.get_stats_dict(plot_type),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_astm_fit(request):
    """Calculate and return ASTM fit data - matching BERT_Reader implementation exactly"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        restraint = data.get('restraint', 'None')
        condition = data.get('condition', 'Normal')
        height = int(data.get('height', 0))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Load data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            acc_data = astm_data if file_info['type'] == 'astm' else gb_data
            acc_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0,
                             seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        # Calculate ASTM sustained acceleration - matching BERT_Reader MplPlot.addplotxyz exactly
        plot_data = acc_data.std_data
        fs = acc_data.fs
        
        # Extended x_axis with same sampling as BERT_Reader
        x_axis = _generate_astm_time_axis()
        
        # Calculate window sizes in samples (matching BERT_Reader)
        window_sizes = [int(t * fs) for t in x_axis]
        
        # Get instantaneous values (matching BERT_Reader MplPlot.addplotxyz exactly)
        # For x-axis: max(0, max) for positive, min(0, min) for negative
        d0px = max(0, np.max(plot_data.iloc[:, 1].values))
        d0nx = min(0, np.min(plot_data.iloc[:, 1].values))
        # For y-axis: max(0, max) for positive, min(0, min) for negative
        d0py = max(0, np.max(plot_data.iloc[:, 2].values))
        d0ny = min(0, np.min(plot_data.iloc[:, 2].values))
        # For z-axis: baseline is 1, so max(1, max) for positive, min(1, min) for negative
        d0pz = max(1, np.max(plot_data.iloc[:, 3].values))
        d0nz = min(1, np.min(plot_data.iloc[:, 3].values))
        
        # Calculate sustained acceleration for all window sizes using ProcessASTM
        results_p = []
        results_n = []
        
        for dt in window_sizes:
            dp, dn = process_ASTM(plot_data, dt)
            results_p.append(dp)
            results_n.append(dn)
        
        # Extract x, y, z values for plotting (matching BERT_Reader structure)
        # results_p[n] = [ax(+), ay(+), az(+)]
        # results_n[n] = [ax(-), ay(-), az(-)]
        ax_p = [d0px] + [r[0] for r in results_p]
        ax_n = [d0nx] + [r[0] for r in results_n]
        ay_p = [d0py] + [r[1] for r in results_p]
        ay_n = [d0ny] + [r[1] for r in results_n]
        az_p = [d0pz] + [r[2] for r in results_p]
        az_n = [d0nz] + [r[2] for r in results_n]
        
        # Calculate height coefficient using the proper coef function from sci_calculation
        ht = float(height) if height else 0
        coef_x = coef(ht, 'x')
        coef_z = coef(ht, 'z')
        
        # Apply condition multiplier (matching original PyQt implementation)
        if condition == 'E-Stop' or condition == 'Expected/Permitted Bumping':
            cond_mult = 1.25
        else:
            cond_mult = 1.0
        
        # Generate egg-shaped contours for ASTM using the original functions from sci_calculation
        egg_xy_x, egg_xy_y = eggXY(2 * coef_x, 6 * coef_x, 3 * coef_x)
        egg_xz_x, egg_xz_z = eggXZ(2 * coef_z, 6 * coef_z, 2 * coef_z, 6 * coef_z)
        egg_yz_y, egg_yz_z = eggYZ(3 * coef_z, 2 * coef_z, 6 * coef_z)
        
        egg_xy = {'x': egg_xy_x.tolist(), 'y': egg_xy_y.tolist()}
        egg_xz = {'x': egg_xz_x.tolist(), 'z': egg_xz_z.tolist()}
        egg_yz = {'y': egg_yz_y.tolist(), 'z': egg_yz_z.tolist()}
        
        # Generate restraint-specific contours
        restraint_contours = _get_restraint_contours(restraint, cond_mult, coef_x, coef_z)
        
        # Prepare response data - matching BERT_Reader structure
        astm_data = {
            'time_axis': [0.002] + x_axis,  # 0.002 represents instantaneous
            'ax_positive': ax_p,
            'ax_negative': ax_n,
            'ay_positive': ay_p,
            'ay_negative': ay_n,
            'az_positive': az_p,
            'az_negative': az_n,
            'raw_x': plot_data.iloc[:, 1].values.tolist(),
            'raw_y': plot_data.iloc[:, 2].values.tolist(),
            'raw_z': plot_data.iloc[:, 3].values.tolist(),
            'time': plot_data.iloc[:, 0].values.tolist(),
        }
        
        # ASTM standard limit lines for ax, ay, az plots
        astm_limits = {
            'ax_positive': {'x': [0.2, 0.5, 14], 'y': [6 * coef_x, 4 * coef_x, 2.5 * coef_x]},
            'ax_negative': {'x': [0.2, 0.5, 14], 'y': [-2 * coef_x, -1.5 * coef_x, -1.5 * coef_x]},
            'ay_positive': {'x': [0.2, 1, 14], 'y': [3 * coef_x, 2 * coef_x, 2 * coef_x]},
            'az_positive': {'x': [0.2, 1, 14], 'y': [6 * coef_z, 4 * coef_z, 2 * coef_z]},
            'az_negative': {'x': [0.2, 0.5, 14], 'y': [-2 * coef_z, -1.5 * coef_z, -1.2 * coef_z]},
        }
        
        # Generate restraint-specific limit lines for sustained acceleration (matching BERT_Reader addDisneyStd)
        restraint_limits = _get_restraint_limits(restraint, cond_mult, coef_x, coef_z)
        
        # Detect reversals for egg plot analysis
        fs = acc_data.fs
        time_data = plot_data.iloc[:, 0].values.tolist()
        x_data = plot_data.iloc[:, 1].values.tolist()
        y_data = plot_data.iloc[:, 2].values.tolist()
        z_data = plot_data.iloc[:, 3].values.tolist()
        
        z_reversals = detect_z_acceleration_reversal(z_data, time_data, fs)
        xy_reversals = detect_xy_acceleration_reversal(x_data, y_data, time_data, fs)
        
        # Convert numpy types to Python native types for JSON serialization
        # Z reversals have additional fields (pre_window_start, pre_window_end, value_diff)
        def convert_z_reversal(r):
            return {
                'window_start': float(r.get('window_start', 0)),
                'window_end': float(r.get('window_end', 0)),
                'min_time': float(r.get('min_time', 0)),
                'max_time': float(r.get('max_time', 0)),
                'min_value': float(r.get('min_value', 0)),
                'max_value': float(r.get('max_value', 0)),
                'pre_window_start': float(r.get('pre_window_start', 0)),
                'pre_window_end': float(r.get('pre_window_end', 0)),
                'window_start_idx': int(r.get('window_start_idx', 0)),
                'window_end_idx': int(r.get('window_end_idx', 0)),
                'min_idx': int(r.get('min_idx', 0)),
                'max_idx': int(r.get('max_idx', 0)),
                'value_diff': float(r.get('value_diff', 0))
            }
        
        # XY reversals have simpler structure
        def convert_xy_reversal(r):
            return {
                'window_start': float(r.get('window_start', 0)),
                'window_end': float(r.get('window_end', 0)),
                'min_time': float(r.get('min_time', 0)),
                'max_time': float(r.get('max_time', 0)),
                'min_value': float(r.get('min_value', 0)),
                'max_value': float(r.get('max_value', 0)),
                'axis': r.get('axis', 'unknown'),
                'window_start_idx': int(r.get('window_start_idx', 0)),
                'window_end_idx': int(r.get('window_end_idx', 0)),
                'min_idx': int(r.get('min_idx', 0)),
                'max_idx': int(r.get('max_idx', 0))
            }
        
        z_reversals_json = [convert_z_reversal(r) for r in z_reversals]
        
        xy_reversals_json = {
            'x_reversals': [convert_xy_reversal(r) for r in xy_reversals.get('x_reversals', [])],
            'y_reversals': [convert_xy_reversal(r) for r in xy_reversals.get('y_reversals', [])]
        }
        
        return JsonResponse({
            'success': True,
            'astm_data': astm_data,
            'astm_limits': astm_limits,
            'egg_contours': {
                'xy': egg_xy,
                'xz': egg_xz,
                'yz': egg_yz,
            },
            'restraint_contours': restraint_contours,
            'restraint_limits': restraint_limits,
            'restraint': restraint,
            'condition': condition,
            'height': height,
            'z_reversals': z_reversals_json,
            'xy_reversals': xy_reversals_json,
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_gb_fit(request):
    """Calculate and return GB fit data"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Load data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            acc_data = gb_data if file_info['type'] == 'gb' else astm_data
            acc_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0,
                             seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        # Calculate GB sustained acceleration
        plot_data = acc_data.std_data
        fs = acc_data.fs
        
        # Generate time axis for GB calculations
        x_axis = _generate_gb_time_axis()
        results_p = []
        results_n = []
        
        for dt_seconds in x_axis:
            dt_samples = int(dt_seconds * fs)
            dp, dn = process_GB(plot_data, dt_samples)
            results_p.append(dp)
            results_n.append(dn)
        
        # Prepare response data
        gb_data = {
            'time_axis': [0.002] + x_axis,
            'ay_positive': [max(0, max(plot_data.iloc[:, 2].values))] + [r[0] for r in results_p],
            'ay_negative': [min(0, min(plot_data.iloc[:, 2].values))] + [r[0] for r in results_n],
            'az_positive': [max(1, max(plot_data.iloc[:, 3].values))] + [r[1] for r in results_p],
            'az_negative': [min(1, min(plot_data.iloc[:, 3].values))] + [r[1] for r in results_n],
            'raw_x': plot_data.iloc[:, 1].values.tolist(),
            'raw_y': plot_data.iloc[:, 2].values.tolist(),
            'raw_z': plot_data.iloc[:, 3].values.tolist(),
            'time': plot_data.iloc[:, 0].values.tolist(),
        }
        
        # GB standard limit lines
        gb_limits = {
            'ay_positive': {'x': [0.01, 0.2, 1, 4], 'y': [5, 2, 2, 2]},
            'ay_negative': {'x': [0.01, 0.2, 1, 4], 'y': [-5, -2, -2, -2]},
            'az_positive': {'x': [0, 1, 2, 3, 4], 'y': [6, 6, 4, 4, 4]},
            'az_negative': {'x': [0, 1, 2, 3, 4], 'y': [-2, -1.5, -1.5, -1.5, -1.5]},
        }
        
        # GB combined contour
        gb_contour = {
            'x': [-1.8, -1.62, -0.54, 0, 1.8, 5.4, 6],
            'y_pos': [0, 0.6, 1.8, 2, 1.8, 0.6, 0],
            'y_neg': [0, -0.6, -1.8, -2, -1.8, -0.6, 0],
        }
        
        return JsonResponse({
            'success': True,
            'gb_data': gb_data,
            'gb_limits': gb_limits,
            'gb_contour': gb_contour,
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_zone_analysis(request):
    """Calculate and return acceleration zone analysis with zone colors and classification"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Load data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            acc_data = gb_data if file_info['type'] == 'gb' else astm_data
            acc_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0,
                             seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        plot_data = acc_data.std_data
        x_data = plot_data.iloc[:, 1].values.tolist()
        z_data = plot_data.iloc[:, 3].values.tolist()
        time_data = plot_data.iloc[:, 0].values.tolist()
        
        # Analyze zones and get colors for each point
        zone_colors = []
        zone_labels = []
        for x, z in zip(x_data, z_data):
            zone = _get_zone(x, z)
            zone_colors.append(_get_zone_color(zone))
            zone_labels.append(zone)
        
        # Analyze zone durations
        zone_analysis = _analyze_acceleration_zones(x_data, z_data, time_data, acc_data.fs)
        
        return JsonResponse({
            'success': True,
            'zone_data': {
                'x': x_data,
                'z': z_data,
                'time': time_data,
                'colors': zone_colors,
                'zone_labels': zone_labels,
            },
            'zone_analysis': zone_analysis,
            'zone_boundaries': _get_zone_boundaries(),
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_reversal_analysis(request):
    """Calculate and return reversal analysis"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Load data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            acc_data = gb_data if file_info['type'] == 'gb' else astm_data
            acc_data.reformat(overwrite=True, setting_angle=True, pitch_angle=0,
                             seatback_angle=0, roll_angle=0, yaw_angle=0, cutoff=cutoff)
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        plot_data = acc_data.std_data
        x_data = plot_data.iloc[:, 1].values
        y_data = plot_data.iloc[:, 2].values
        z_data = plot_data.iloc[:, 3].values
        time_data = plot_data.iloc[:, 0].values
        fs = acc_data.fs
        
        # Detect reversals
        z_reversals = detect_z_acceleration_reversal(z_data, time_data, fs)
        xy_reversals = detect_xy_acceleration_reversal(x_data, y_data, time_data, fs)
        
        # Format Z reversals for frontend
        z_reversal_list = []
        for r in z_reversals:
            z_reversal_list.append({
                'time': r.get('min_time', 0),
                'value': r.get('min_value', 0)
            })
        
        # Format XY reversals for frontend
        xy_reversal_list = []
        for r in xy_reversals.get('x_reversals', []):
            xy_reversal_list.append({
                'axis': 'X',
                'min_time': r.get('min_time', 0),
                'max_time': r.get('max_time', 0),
                'min_value': r.get('min_value', 0),
                'max_value': r.get('max_value', 0)
            })
        for r in xy_reversals.get('y_reversals', []):
            xy_reversal_list.append({
                'axis': 'Y',
                'min_time': r.get('min_time', 0),
                'max_time': r.get('max_time', 0),
                'min_value': r.get('min_value', 0),
                'max_value': r.get('max_value', 0)
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'time': time_data.tolist(),
                'x': x_data.tolist(),
                'y': y_data.tolist(),
                'z': z_data.tolist(),
            },
            'reversals': z_reversal_list,
            'z_reversals': z_reversals,
            'xy_reversals': xy_reversal_list,
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_data(request):
    """Edit data (add/multiply values, change angles)"""
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        operation = data.get('operation')  # 'add', 'multiply', 'angle', 'truncate'
        values = data.get('values', [])
        cutoff = int(data.get('cutoff', DEFAULT_CUTOFF_FREQUENCY))
        
        if 'accel_data' not in request.session or filename not in request.session['accel_data']:
            return JsonResponse({'error': 'Data not found'}, status=404)
        
        file_info = request.session['accel_data'][filename]
        file_path = os.path.join(settings.MEDIA_ROOT, file_info['file_path'])
        
        # Load data
        if file_info['type'] in ['gb', 'astm']:
            raw_data = RawData(file_path)
            gb_data, astm_data = raw_data.export_data()
            acc_data = gb_data if file_info['type'] == 'gb' else astm_data
        else:
            acc_data = AccData(file_path, cutoff=cutoff)
        
        # Perform operation
        if operation == 'add' or operation == 'multiply':
            acc_data.edit_data(operation, values, cutoff)
        elif operation == 'angle':
            acc_data.reformat(overwrite=True, setting_angle=True,
                            pitch_angle=values.get('pitch', 0),
                            seatback_angle=values.get('seatback', 0),
                            roll_angle=values.get('roll', 0),
                            yaw_angle=values.get('yaw', 0),
                            cutoff=cutoff)
        elif operation == 'truncate':
            acc_data.truncate_data(values.get('start', 0), values.get('end', 10), cutoff)
        
        return JsonResponse({
            'success': True,
            'data': acc_data.to_dict('Standard'),
            'stats': acc_data.get_stats_dict('Standard'),
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_data(request):
    """Clear all data from session"""
    if 'accel_data' in request.session:
        del request.session['accel_data']
    return JsonResponse({'success': True})


def _generate_astm_time_axis():
    """Generate time axis for ASTM calculations"""
    x_axis = [
        0.02, 0.0225, 0.025, 0.0275, 0.03, 0.0325, 0.035, 0.0375,
        0.04, 0.0425, 0.045, 0.0475, 0.05, 0.0525, 0.055, 0.0575,
        0.06, 0.0625, 0.065, 0.0675, 0.07, 0.0725, 0.075, 0.0775,
        0.08, 0.0825, 0.085, 0.0875, 0.09, 0.0925, 0.095, 0.0975,
        0.1, 0.105, 0.11, 0.115, 0.12, 0.125, 0.13, 0.135, 0.14, 0.145,
        0.15, 0.155, 0.16, 0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195,
        0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29,
        0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39,
        0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49,
        0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725,
        0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975,
        1, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45,
        1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95,
        2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
        3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9,
        4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
        5, 5.25, 5.5, 5.75, 6, 6.25, 6.5, 6.75, 7, 7.25,
        7.5, 7.75, 8, 8.25, 8.5, 8.75, 9, 9.25, 9.5, 9.75,
        10, 10.25, 10.5, 10.75, 11, 11.25, 11.5, 11.75, 12, 12.25,
        12.5, 12.75, 13, 13.25, 13.5, 13.75, 14
    ]
    return x_axis


def _generate_gb_time_axis():
    """Generate time axis for GB calculations"""
    x_axis = []
    # 0.02 to 0.1: 0.0025s increments
    x_axis.extend([round(x, 4) for x in [0.02 + i * 0.0025 for i in range(int((0.1 - 0.02) / 0.0025))]])
    # 0.1 to 0.2: 0.005s increments
    x_axis.extend([round(x, 4) for x in [0.1 + i * 0.005 for i in range(int((0.2 - 0.1) / 0.005))]])
    # 0.2 to 0.5: 0.01s increments
    x_axis.extend([round(x, 4) for x in [0.2 + i * 0.01 for i in range(int((0.5 - 0.2) / 0.01))]])
    # 0.5 to 1: 0.025s increments
    x_axis.extend([round(x, 4) for x in [0.5 + i * 0.025 for i in range(int((1 - 0.5) / 0.025))]])
    # 1 to 2: 0.05s increments
    x_axis.extend([round(x, 4) for x in [1 + i * 0.05 for i in range(int((2 - 1) / 0.05))]])
    # 2 to 5: 0.1s increments
    x_axis.extend([round(x, 4) for x in [2 + i * 0.1 for i in range(int((5 - 2) / 0.1))]])
    # 5 to 14: 0.25s increments
    x_axis.extend([round(x, 4) for x in [5 + i * 0.25 for i in range(int((14.25 - 5) / 0.25))]])
    return x_axis


def _analyze_acceleration_zones(x_data, z_data, time_data, fs):
    """Analyze which zones the acceleration data falls into"""
    if len(time_data) >= 2:
        time_interval = time_data[1] - time_data[0]
    else:
        time_interval = 1.0 / fs
    
    min_duration = 0.2
    min_points = int(min_duration / time_interval)
    
    # Determine zone for each point
    zone_list = []
    for x, z in zip(x_data, z_data):
        zone = _get_zone(x, z)
        zone_list.append(zone)
    
    # Find consecutive zones
    zone_durations = {}
    i = 0
    n = len(zone_list)
    
    while i < n:
        current_zone = zone_list[i]
        start_idx = i
        
        while i < n and zone_list[i] == current_zone:
            i += 1
        end_idx = i
        
        num_points = end_idx - start_idx
        if num_points >= min_points:
            start_time = float(time_data[start_idx])
            end_time = float(time_data[end_idx - 1])
            duration = end_time - start_time
            
            if current_zone not in zone_durations:
                zone_durations[current_zone] = []
            zone_durations[current_zone].append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration
            })
    
    # Find most severe zone
    zone_severity = {"Zone 5": 5, "Zone 4": 4, "Zone 3": 3, "Zone 2": 2, "Zone 1": 1}
    qualifying_zones = []
    
    for zone, durations in zone_durations.items():
        if zone in zone_severity:
            qualifying_zones.append((zone_severity[zone], zone, durations))
    
    qualifying_zones.sort(key=lambda x: x[0], reverse=True)
    
    return {
        'zone_durations': zone_durations,
        'most_severe': qualifying_zones[0] if qualifying_zones else None
    }


def _get_zone(x, y):
    """Determine which zone a point falls into"""
    def is_left_of_line(x, y):
        line_x_at_y = -3.5 * y
        return x < line_x_at_y
    
    if y > 0.7:
        if x < -1.2:
            return "Zone 4"
        elif x < -0.7:
            return "Zone 3"
        elif x < -0.2:
            return "Zone 2"
        else:
            return "Zone 1"
    elif y > 0.2:
        if x < -1.2:
            return "Zone 4"
        elif x < -0.7:
            return "Zone 3"
        elif x < 0.2:
            return "Zone 2"
        else:
            return "Zone 1"
    elif y > 0:
        if is_left_of_line(x, y) and x < -0.2:
            return "Zone 4"
        elif is_left_of_line(x, y) and -0.2 <= x <= 0:
            return "Zone 5"
        else:
            return "Zone 3"
    elif y > -0.2:
        if is_left_of_line(x, y) and x < 0.7:
            return "Zone 5"
        elif not is_left_of_line(x, y) and x < 0.2:
            return "Zone 5"
        else:
            return "Zone 4"
    else:
        return "Zone 5"


def _coef(ht, axis):
    """Calculate height coefficient for ASTM limits"""
    # Simplified coefficient calculation
    return 1.0


def _generate_egg_xy(a, b, c):
    """Generate egg-shaped contour for XY plane.
    Exactly matching original PyQtGraphPlot.eggXY(a, b, c)
    """
    import numpy as np
    theta = np.linspace(0, 2*np.pi, 200)
    x = a * np.cos(theta)
    y = np.where(np.abs(theta - np.pi) < np.pi/2,
                 c * np.sin(theta),
                 b * np.sin(theta))
    return {'x': x.tolist(), 'y': y.tolist()}


def _generate_egg_xz(a, b, c, d):
    """Generate egg-shaped contour for XZ plane.
    Exactly matching original PyQtGraphPlot.eggXZ(a, b, c, d)
    """
    import numpy as np
    theta = np.linspace(0, 2*np.pi, 200)
    x = np.where(np.abs(theta - np.pi) < np.pi/2,
                 a * np.cos(theta),
                 b * np.cos(theta))
    z = np.where(np.abs(theta - np.pi/2) < np.pi/2,
                 c * np.sin(theta),
                 d * np.sin(theta))
    return {'x': x.tolist(), 'z': z.tolist()}


def _generate_egg_yz(a, b, c):
    """Generate egg-shaped contour for YZ plane.
    Exactly matching original PyQtGraphPlot.eggYZ(a, b, c)
    """
    import numpy as np
    theta = np.linspace(0, 2*np.pi, 200)
    y = a * np.cos(theta)
    z = np.where(np.abs(theta - np.pi/2) < np.pi/2,
                 b * np.sin(theta),
                 c * np.sin(theta))
    return {'y': y.tolist(), 'z': z.tolist()}


def _get_restraint_contours(restraint, cond_mult, coef_x, coef_z):
    """Generate restraint-specific contour data matching original PyQt implementation exactly.
    
    Key differences from base ASTM contours:
    - Upper Body: Has both solid (0s) and dashed (0.2s) contours
    - Group Lower Body: XZ and YZ contours have +1 offset applied to z values
    - Individual Lower Body: Standard contours without offset
    - No/Convenience Restraint: XZ and YZ contours have +1 offset applied to z values
    """
    import numpy as np
    contours = {}
    
    if restraint == 'Upper Body':
        # Solid contours (0s)
        xa, ya = eggXY(2 * cond_mult * coef_x, 3.6 * cond_mult * coef_x, 3 * cond_mult * coef_x)
        # Dashed contours (0.2s)
        xaa, yaa = eggXY(1.6 * cond_mult * coef_x, 3.6 * cond_mult * coef_x, 2.4 * cond_mult * coef_x)
        xb, yb = eggXZ(2 * cond_mult * coef_z, 3.6 * cond_mult * coef_z, 2 * cond_mult * coef_z, 5 * cond_mult * coef_z)
        xbb, ybb = eggXZ(1.6 * cond_mult * coef_z, 3.6 * cond_mult * coef_z, 1.4 * cond_mult * coef_z, 4.8 * cond_mult * coef_z)
        xc, yc = eggYZ(3 * cond_mult * coef_z, 2 * cond_mult * coef_z, 5 * cond_mult * coef_z)
        xcc, ycc = eggYZ(2.4 * cond_mult * coef_z, 1.4 * cond_mult * coef_z, 4.8 * cond_mult * coef_z)
        
        contours['xy'] = {'x': xa.tolist(), 'y': ya.tolist()}
        contours['xy_dash'] = {'x': xaa.tolist(), 'y': yaa.tolist()}
        contours['xz'] = {'x': xb.tolist(), 'z': yb.tolist()}
        contours['xz_dash'] = {'x': xbb.tolist(), 'z': ybb.tolist()}
        contours['yz'] = {'y': xc.tolist(), 'z': yc.tolist()}
        contours['yz_dash'] = {'y': xcc.tolist(), 'z': ycc.tolist()}
        
    elif restraint == 'Group Lower Body':
        # Solid contours (0s)
        xa, ya = eggXY(1.7 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 2.4 * cond_mult * coef_x)
        # Dashed contours (0.2s)
        xaa, yaa = eggXY(1.4 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 2.1 * cond_mult * coef_x)
        # XZ with +1 offset on z (matching original: xb, 1 + yb)
        xb, yb = eggXZ(1.7 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 2 * cond_mult * coef_z, 3.5 * cond_mult * coef_z)
        xbb, ybb = eggXZ(1.4 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 1 * cond_mult * coef_z, 3 * cond_mult * coef_z)
        # YZ with +1 offset on z (matching original: xc, 1 + yc)
        xc, yc = eggYZ(2.4 * cond_mult * coef_z, 2 * cond_mult * coef_z, 3.5 * cond_mult * coef_z)
        xcc, ycc = eggYZ(2.1 * cond_mult * coef_z, 1 * cond_mult * coef_z, 3 * cond_mult * coef_z)
        
        contours['xy'] = {'x': xa.tolist(), 'y': ya.tolist()}
        contours['xy_dash'] = {'x': xaa.tolist(), 'y': yaa.tolist()}
        # Apply +1 offset to z values for Group Lower Body
        contours['xz'] = {'x': xb.tolist(), 'z': (yb + 1).tolist()}
        contours['xz_dash'] = {'x': xbb.tolist(), 'z': (ybb + 1).tolist()}
        contours['yz'] = {'y': xc.tolist(), 'z': (yc + 1).tolist()}
        contours['yz_dash'] = {'y': xcc.tolist(), 'z': (ycc + 1).tolist()}
        
    elif restraint == 'Individual Lower Body':
        # Solid contours (0s)
        xa, ya = eggXY(1.8 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 2.6 * cond_mult * coef_x)
        # Dashed contours (0.2s)
        xaa, yaa = eggXY(1.5 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 2.2 * cond_mult * coef_x)
        xb, yb = eggXZ(1.8 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 1.8 * cond_mult * coef_z, 4.8 * cond_mult * coef_z)
        # Note: Original has a bug - 4.5 * coef(ht, 'z') should be 4.5 * cond_mult * coef_z
        xbb, ybb = eggXZ(1.5 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 1.2 * cond_mult * coef_z, 4.5 * cond_mult * coef_z)
        xc, yc = eggYZ(2.6 * cond_mult * coef_z, 1.8 * cond_mult * coef_z, 4.8 * cond_mult * coef_z)
        xcc, ycc = eggYZ(2.2 * cond_mult * coef_z, 1.2 * cond_mult * coef_z, 4.5 * cond_mult * coef_z)
        
        contours['xy'] = {'x': xa.tolist(), 'y': ya.tolist()}
        contours['xy_dash'] = {'x': xaa.tolist(), 'y': yaa.tolist()}
        contours['xz'] = {'x': xb.tolist(), 'z': yb.tolist()}
        contours['xz_dash'] = {'x': xbb.tolist(), 'z': ybb.tolist()}
        contours['yz'] = {'y': xc.tolist(), 'z': yc.tolist()}
        contours['yz_dash'] = {'y': xcc.tolist(), 'z': ycc.tolist()}
        
    else:  # No Restraint or Convenience Restraint
        # Solid contours (0s)
        xa, ya = eggXY(1.5 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 1.8 * cond_mult * coef_x)
        # Dashed contours (0.2s)
        xaa, yaa = eggXY(1.2 * cond_mult * coef_x, 2.5 * cond_mult * coef_x, 1.2 * cond_mult * coef_x)
        # XZ with +1 offset on z (matching original: xb, 1 + yb)
        xb, yb = eggXZ(1.5 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 1.2 * cond_mult * coef_z, 3 * cond_mult * coef_z)
        xbb, ybb = eggXZ(1.2 * cond_mult * coef_z, 2.5 * cond_mult * coef_z, 0.8 * cond_mult * coef_z, 2.8 * cond_mult * coef_z)
        # YZ with +1 offset on z (matching original: xc, 1 + yc)
        xc, yc = eggYZ(1.8 * cond_mult * coef_z, 1.2 * cond_mult * coef_z, 3 * cond_mult * coef_z)
        xcc, ycc = eggYZ(1.2 * cond_mult * coef_z, 0.8 * cond_mult * coef_z, 2.8 * cond_mult * coef_z)
        
        contours['xy'] = {'x': xa.tolist(), 'y': ya.tolist()}
        contours['xy_dash'] = {'x': xaa.tolist(), 'y': yaa.tolist()}
        # Apply +1 offset to z values for No/Convenience Restraint
        contours['xz'] = {'x': xb.tolist(), 'z': (yb + 1).tolist()}
        contours['xz_dash'] = {'x': xbb.tolist(), 'z': (ybb + 1).tolist()}
        contours['yz'] = {'y': xc.tolist(), 'z': (yc + 1).tolist()}
        contours['yz_dash'] = {'y': xcc.tolist(), 'z': (ycc + 1).tolist()}
    
    return contours


def _get_zone_color(zone):
    """Return color for each zone matching BERT_Reader implementation."""
    zone_colors = {
        'Zone 1': '#ADFF2F',  # greenyellow
        'Zone 2': '#FFFF00',  # yellow
        'Zone 3': '#FFA500',  # orange
        'Zone 4': '#FFB6C1',  # lightpink
        'Zone 5': '#FF0000',  # red
    }
    return zone_colors.get(zone, '#3498db')


def _get_zone_boundaries():
    """Return zone boundary polygons for visualization.
    Matching BERT_Reader AccZonePlot implementation - all zones covered with no white background.
    Zone boundaries exactly match the original PyQt implementation.
    """
    # Zone 5 (red) - y <= -0.2 (entire bottom region)
    zone5_base = {
        'x': [-6, 6, 6, -6],
        'y': [-4, -4, -0.2, -0.2],
        'color': 'rgba(255, 0, 0, 0.3)'
    }
    
    # Zone 5 (red) - region in -0.2 < y <= 0, left of sloping line (x < -3.5y) AND x < 0.7
    # This covers from x=-6 to the sloping line
    zone5_mid_left = {
        'x': [-6, -6, 0, 0.7, 0.7, -6],
        'y': [-0.2, 0, 0, -0.2, -0.2, -0.2],
        'color': 'rgba(255, 0, 0, 0.3)'
    }
    
    # Zone 5 (red) - small triangle in 0 < y <= 0.2, between x=-0.2 and sloping line
    # Line goes from (0,0) to (-0.7, 0.2), at y=0.2/3.5 ~= 0.057, x = -0.2
    zone5_tri = {
        'x': [-0.2, 0, -0.2],
        'y': [0, 0, 0.2/3.5],
        'color': 'rgba(255, 0, 0, 0.3)'
    }
    
    # Zone 5 (red) - region in 0 < y <= 0.2, right portion (x > 0 and x < 0.7, below line)
    zone5_mid_right = {
        'x': [0, 0.7, 0.7, 0],
        'y': [0, -0.2, 0, 0],
        'color': 'rgba(255, 0, 0, 0.3)'
    }
    
    # Zone 4 (lightpink) - region in -0.2 < y <= 0, right of sloping line
    # From line to x=6
    zone4_bottom = {
        'x': [0.7, 6, 6, 0.2, 0, -0.7, 0.7],
        'y': [-0.2, -0.2, 0, 0, 0.2, 0.2, -0.2],
        'color': 'rgba(255, 182, 193, 0.3)'
    }
    
    # Zone 4 (lightpink) - 0 < y <= 0.2, left of line AND x < -0.2
    zone4_mid_left = {
        'x': [-6, -6, -0.7, -0.2],
        'y': [0, 0.2, 0.2, 0],
        'color': 'rgba(255, 182, 193, 0.3)'
    }
    
    # Zone 4 (lightpink) - x < -1.2, 0.2 < y <= 0.7
    zone4_mid2 = {
        'x': [-6, -1.2, -1.2, -6],
        'y': [0.2, 0.2, 0.7, 0.7],
        'color': 'rgba(255, 182, 193, 0.3)'
    }
    
    # Zone 4 (lightpink) - x < -1.2, y > 0.7
    zone4_top = {
        'x': [-6, -1.2, -1.2, -6],
        'y': [0.7, 0.7, 4, 4],
        'color': 'rgba(255, 182, 193, 0.3)'
    }
    
    # Zone 3 (orange) - 0 < y <= 0.2, right of line
    zone3_mid = {
        'x': [-0.7, 6, 6, -0.7],
        'y': [0.2, 0.2, 0, 0],
        'color': 'rgba(255, 165, 0, 0.3)'
    }
    
    # Zone 3 (orange) - -1.2 <= x < -0.7, 0.2 < y <= 0.7
    zone3_mid2 = {
        'x': [-1.2, -0.7, -0.7, -1.2],
        'y': [0.2, 0.2, 0.7, 0.7],
        'color': 'rgba(255, 165, 0, 0.3)'
    }
    
    # Zone 3 (orange) - -1.2 <= x < -0.7, y > 0.7
    zone3_top = {
        'x': [-1.2, -0.7, -0.7, -1.2],
        'y': [0.7, 0.7, 4, 4],
        'color': 'rgba(255, 165, 0, 0.3)'
    }
    
    # Zone 2 (yellow) - -0.7 <= x < 0.2, 0.2 < y <= 0.7
    zone2_mid = {
        'x': [-0.7, 0.2, 0.2, -0.7],
        'y': [0.2, 0.2, 0.7, 0.7],
        'color': 'rgba(255, 255, 0, 0.3)'
    }
    
    # Zone 2 (yellow) - -0.7 <= x < -0.2, y > 0.7
    zone2_top = {
        'x': [-0.7, -0.2, -0.2, -0.7],
        'y': [0.7, 0.7, 4, 4],
        'color': 'rgba(255, 255, 0, 0.3)'
    }
    
    # Zone 1 (greenyellow) - x >= 0.2, 0.2 < y <= 0.7
    zone1_mid = {
        'x': [0.2, 6, 6, 0.2],
        'y': [0.2, 0.2, 0.7, 0.7],
        'color': 'rgba(173, 255, 47, 0.3)'
    }
    
    # Zone 1 (greenyellow) - x >= -0.2, y > 0.7
    zone1_top = {
        'x': [-0.2, 6, 6, -0.2],
        'y': [0.7, 0.7, 4, 4],
        'color': 'rgba(173, 255, 47, 0.3)'
    }
    
    return {
        'zone5': [zone5_base, zone5_mid_left, zone5_tri, zone5_mid_right],
        'zone4': [zone4_bottom, zone4_mid_left, zone4_mid2, zone4_top],
        'zone3': [zone3_mid, zone3_mid2, zone3_top],
        'zone2': [zone2_mid, zone2_top],
        'zone1': [zone1_mid, zone1_top],
    }


def _get_restraint_limits(restraint, cond_mult, coef_x, coef_z):
    """
    Generate restraint-specific limit lines for sustained acceleration plots.
    Matching BERT_Reader MplPlot.addDisneyStd implementation.
    
    Returns dictionary with ax_positive, ax_negative, ay_positive, az_positive, az_negative limits.
    """
    import numpy as np
    
    # Base ASTM limit arrays from BERT_Reader
    frontASTM = np.array([-2, -2, -1.5, -1.5])
    backASTM = np.array([6, 6, 6, 4, 4, 3, 3, 2.5, 2.5])
    lrASTM = np.array([3, 3, 3, 2, 2])
    upASTM = np.array([-2, -2, -1.5, -1.5, -1.2, -1.2])
    downASTM = np.array([6, 6, 6, 4, 4, 3, 3, 2, 2])
    
    # X-axis time points
    ax_time = [0, 0.2, 0.5, 1, 2, 4, 5, 11.8, 12, 14]
    # Y-axis time points
    ay_time = [0, 0.2, 1, 2, 14]
    # Z-axis time points (positive)
    az_pos_time = [0, 0.2, 0.5, 4, 7, 14]
    # Z-axis time points (negative)
    az_neg_time = [0, 0.2, 1, 2, 4, 5, 11.8, 12, 14]
    
    limits = {}
    
    if restraint == 'Upper Body':
        # Calculate restraint-specific limits using np.maximum/np.minimum
        a31 = np.maximum(frontASTM, np.array([-2, -1.6, -1.2, -1.2]) * coef_x)
        a32 = np.minimum(backASTM, np.array([3.6, 3.6, 3.6, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lrASTM, np.array([3, 2.4, 2.4, 1.6, 1.6]) * coef_x)
        a34 = np.maximum(upASTM, np.array([-2, -1.4, -1, -1, -0.7, -0.7]) * coef_z)
        a35 = np.minimum(downASTM, np.array([5, 4.8, 4.8, 3.4, 3.4, 2.6, 2.6, 1.8, 1.8]) * coef_z)
        
        limits = {
            'ax_positive': {'x': ax_time, 'y': (a32 * cond_mult).tolist()},
            'ax_negative': {'x': ax_time[:4], 'y': (a31 * cond_mult).tolist()},
            'ay_positive': {'x': ay_time, 'y': (a33 * cond_mult).tolist()},
            'az_positive': {'x': az_pos_time, 'y': (a35 * cond_mult).tolist()},
            'az_negative': {'x': az_neg_time, 'y': (a34 * cond_mult).tolist()},
        }
        
    elif restraint == 'Group Lower Body':
        a31 = np.maximum(frontASTM, np.array([-2, -1.6, -1.2, -1.2]) * coef_x)
        a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lrASTM, np.array([2.4, 2.1, 2.1, 1.4, 1.4]) * coef_x)
        a34 = np.maximum(upASTM, np.array([-1, 0, 0.2, 0.2, 0.2, 0.2]) * coef_z)
        a35 = np.minimum(downASTM, np.array([4.5, 4, 4, 3.1, 3.1, 2.4, 2.4, 1.7, 1.7]) * coef_z)
        
        limits = {
            'ax_positive': {'x': ax_time, 'y': (a32 * cond_mult).tolist()},
            'ax_negative': {'x': ax_time[:4], 'y': (a31 * cond_mult).tolist()},
            'ay_positive': {'x': ay_time, 'y': (a33 * cond_mult).tolist()},
            'az_positive': {'x': az_pos_time, 'y': (a35 * cond_mult).tolist()},
            'az_negative': {'x': az_neg_time, 'y': (a34 * cond_mult).tolist()},
        }
        
    elif restraint == 'Individual Lower Body':
        a31 = np.maximum(frontASTM, np.array([-1.8, -1.5, -1.1, -1.1]) * coef_x)
        a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lrASTM, np.array([2.6, 2.2, 2.2, 1.5, 1.5]) * coef_x)
        a34 = np.maximum(upASTM, np.array([-1.8, -1.2, -0.9, -0.9, -0.6, -0.6]) * coef_z)
        a35 = np.minimum(downASTM, np.array([4.8, 4.5, 4.5, 3.2, 3.2, 2.5, 2.5, 1.8, 1.8]) * coef_z)
        
        limits = {
            'ax_positive': {'x': ax_time, 'y': (a32 * cond_mult).tolist()},
            'ax_negative': {'x': ax_time[:4], 'y': (a31 * cond_mult).tolist()},
            'ay_positive': {'x': ay_time, 'y': (a33 * cond_mult).tolist()},
            'az_positive': {'x': az_pos_time, 'y': (a35 * cond_mult).tolist()},
            'az_negative': {'x': az_neg_time, 'y': (a34 * cond_mult).tolist()},
        }
        
    else:  # No Restraint or Convenience Restraint
        a31 = np.maximum(frontASTM, np.array([-1.5, -1.2, -0.7, -0.7]) * coef_x)
        a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lrASTM, np.array([1.8, 1.2, 1.2, 0.7, 0.7]) * coef_x)
        a34 = np.maximum(upASTM, np.array([-0.2, 0.2, 0.2, 0.2, 0.2, 0.2]) * coef_z)
        a35 = np.minimum(downASTM, np.array([4, 3.8, 3.8, 2.8, 2.8, 2.2, 2.2, 1.6, 1.6]) * coef_z)
        
        limits = {
            'ax_positive': {'x': ax_time, 'y': (a32 * cond_mult).tolist()},
            'ax_negative': {'x': ax_time[:4], 'y': (a31 * cond_mult).tolist()},
            'ay_positive': {'x': ay_time, 'y': (a33 * cond_mult).tolist()},
            'az_positive': {'x': az_pos_time, 'y': (a35 * cond_mult).tolist()},
            'az_negative': {'x': az_neg_time, 'y': (a34 * cond_mult).tolist()},
        }
    
    return limits
