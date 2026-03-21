import os
import sys
import math
import io
import xlsxwriter
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from datetime import date

# Get the FKM module directory
FKM_DIR = os.path.join(settings.BASE_DIR, 'FKM')

# Global dataframe for calculations
df = pd.Series(dtype='float64')


def get_R(m, a):
    """Calculate stress ratio."""
    return (m - a) / (m + a) if (m + a) != 0 else 0


def index(request):
    """FKM 计算模块主页"""
    return render(request, 'fkm/index.html')


def fatigue_calculator(request):
    """疲劳强度计算器页面"""
    return render(request, 'fkm/fatigue.html')


def static_calculator(request):
    """静强度计算器页面"""
    return render(request, 'fkm/static.html')


def load_material_data(request):
    """加载材料数据"""
    try:
        excel_path = os.path.join(FKM_DIR, 'FKM Structural Steel.xlsx')
        material_type = request.GET.get('type', '0')
        
        if material_type == '0':
            table = pd.read_excel(excel_path, sheet_name='Table 5.1.2')
            materials = []
            for name in ['S185', 'S235', 'S275', 'S355', 'S450']:
                row = table[table['Type'] == name]
                if not row.empty:
                    data = row.iloc[0].to_dict()
                    # Convert numpy types to native Python types
                    materials.append({'name': name, 'data': convert_to_serializable(data)})
                else:
                    materials.append({'name': name, 'data': None})
        else:
            table = pd.read_excel(excel_path, sheet_name='Table 5.1.3')
            materials = []
            for name in ['S275N/NL', 'S355N/NL', 'S420N/NL', 'S275M/ML', 'S355M/ML', 'S420M/ML']:
                row = table[table['Type'] == name]
                if not row.empty:
                    data = row.iloc[0].to_dict()
                    # Convert numpy types to native Python types
                    materials.append({'name': name, 'data': convert_to_serializable(data)})
                else:
                    materials.append({'name': name, 'data': None})
        
        return JsonResponse({'status': 'success', 'materials': materials})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step1(request):
    """疲劳计算 - 步骤 1: 特征服务应力"""
    try:
        data = json.loads(request.body)
        calculation_type = data.get('calculation_type', 'base')
        
        results = []
        
        if calculation_type == 'base':
            sigma_x_max = float(data.get('sigma_x_max', 0))
            sigma_x_min = float(data.get('sigma_x_min', 0))
            sigma_y_max = float(data.get('sigma_y_max', 0))
            sigma_y_min = float(data.get('sigma_y_min', 0))
            t_max = float(data.get('t_max', 0))
            t_min = float(data.get('t_min', 0))
            
            sigma_m_x = 0.5 * (sigma_x_max + sigma_x_min)
            sigma_a_x = 0.5 * (sigma_x_max - sigma_x_min)
            sigma_m_y = 0.5 * (sigma_y_max + sigma_y_min)
            sigma_a_y = 0.5 * (sigma_y_max - sigma_y_min)
            t_m = 0.5 * (t_max + t_min)
            t_a = 0.5 * (t_max - t_min)
            
            Rx = get_R(sigma_m_x, sigma_a_x)
            Ry = get_R(sigma_m_y, sigma_a_y)
            Rt = get_R(t_m, t_a)
            
            results = [
                {'variable': 'σx_max', 'description': 'X Normal Stress Max', 'value': sigma_x_max, 'ref': 'input'},
                {'variable': 'σx_min', 'description': 'X Normal Stress Min', 'value': sigma_x_min, 'ref': 'input'},
                {'variable': 'σy_max', 'description': 'Y Normal Stress Max', 'value': sigma_y_max, 'ref': 'input'},
                {'variable': 'σy_min', 'description': 'Y Normal Stress Min', 'value': sigma_y_min, 'ref': 'input'},
                {'variable': 't_max', 'description': 'Shear Stress Max', 'value': t_max, 'ref': 'input'},
                {'variable': 't_min', 'description': 'Shear Stress Min', 'value': t_min, 'ref': 'input'},
                {'variable': 'σx_m', 'description': 'Mean Stress X', 'value': sigma_m_x, 'ref': 'calculation'},
                {'variable': 'σy_m', 'description': 'Mean Stress Y', 'value': sigma_m_y, 'ref': 'calculation'},
                {'variable': 't_m', 'description': 'Mean Stress Shear', 'value': t_m, 'ref': 'calculation'},
                {'variable': 'σx_a', 'description': 'Stress Amplitude X', 'value': sigma_a_x, 'ref': 'calculation'},
                {'variable': 'σy_a', 'description': 'Stress Amplitude Y', 'value': sigma_a_y, 'ref': 'calculation'},
                {'variable': 't_a', 'description': 'Shear Stress Amplitude', 'value': t_a, 'ref': 'calculation'},
                {'variable': 'Rx', 'description': 'Stress Ratio X', 'value': round(Rx, 3), 'ref': 'calculation'},
                {'variable': 'Ry', 'description': 'Stress Ratio Y', 'value': round(Ry, 3), 'ref': 'calculation'},
                {'variable': 'Rt', 'description': 'Shear Stress Ratio', 'value': round(Rt, 3), 'ref': 'calculation'},
            ]
        else:
            sigma_pp_max = float(data.get('sigma_pp_max', 0))
            sigma_pp_min = float(data.get('sigma_pp_min', 0))
            sigma_pl_max = float(data.get('sigma_pl_max', 0))
            sigma_pl_min = float(data.get('sigma_pl_min', 0))
            t_pl_max = float(data.get('t_pl_max', 0))
            t_pl_min = float(data.get('t_pl_min', 0))
            
            sigma_m_n = 0.5 * (sigma_pp_max + sigma_pp_min)
            sigma_a_n = 0.5 * (sigma_pp_max - sigma_pp_min)
            sigma_m_1 = 0.5 * (sigma_pl_max + sigma_pl_min)
            sigma_a_1 = 0.5 * (sigma_pl_max - sigma_pl_min)
            t_m_1 = 0.5 * (t_pl_max + t_pl_min)
            t_a_1 = 0.5 * (t_pl_max - t_pl_min)
            
            R_pp = get_R(sigma_m_n, sigma_a_n)
            R_pl = get_R(sigma_m_1, sigma_a_1)
            R_t = get_R(t_m_1, t_a_1)
            
            results = [
                {'variable': 'σ⊥_max', 'description': 'Stress Perpendicular to Welds Max', 'value': sigma_pp_max, 'ref': 'input'},
                {'variable': 'σ⊥_min', 'description': 'Stress Perpendicular to Welds Min', 'value': sigma_pp_min, 'ref': 'input'},
                {'variable': 'σ∥_max', 'description': 'Stress Parallel to Welds Max', 'value': sigma_pl_max, 'ref': 'input'},
                {'variable': 'σ∥_min', 'description': 'Stress Parallel to Welds Min', 'value': sigma_pl_min, 'ref': 'input'},
                {'variable': 't_max', 'description': 'Shear Stress Max', 'value': t_pl_max, 'ref': 'input'},
                {'variable': 't_min', 'description': 'Shear Stress Min', 'value': t_pl_min, 'ref': 'input'},
                {'variable': 'σ⊥_m', 'description': 'Mean Stress Perpendicular', 'value': sigma_m_n, 'ref': 'calculation'},
                {'variable': 'σ∥_m', 'description': 'Mean Stress Parallel', 'value': sigma_m_1, 'ref': 'calculation'},
                {'variable': 't_m', 'description': 'Mean Stress Shear', 'value': t_m_1, 'ref': 'calculation'},
                {'variable': 'σ⊥_a', 'description': 'Perpendicular Stress Amplitude', 'value': sigma_a_n, 'ref': 'calculation'},
                {'variable': 'σ∥_a', 'description': 'Parallel Stress Amplitude', 'value': sigma_a_1, 'ref': 'calculation'},
                {'variable': 't_a', 'description': 'Shear Stress Amplitude', 'value': t_a_1, 'ref': 'calculation'},
                {'variable': 'R⊥', 'description': 'Perpendicular Stress Ratio', 'value': round(R_pp, 3), 'ref': 'calculation'},
                {'variable': 'R∥', 'description': 'Parallel Stress Ratio', 'value': round(R_pl, 3), 'ref': 'calculation'},
                {'variable': 'Rt', 'description': 'Shear Stress Ratio', 'value': round(R_t, 3), 'ref': 'calculation'},
            ]
        
        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step2(request):
    """疲劳计算 - 步骤 2: 材料属性"""
    try:
        data = json.loads(request.body)
        material_name = data.get('material_name', '')
        material_type = data.get('material_type', '0')
        d_eff = float(data.get('d_eff', 10))
        ka_index = int(data.get('ka_index', 0))
        fatigue_factor_index = int(data.get('fatigue_factor_index', 0))
        
        excel_path = os.path.join(FKM_DIR, 'FKM Structural Steel.xlsx')
        
        if material_type == '0':
            table = pd.read_excel(excel_path, sheet_name='Table 5.1.2')
        else:
            table = pd.read_excel(excel_path, sheet_name='Table 5.1.3')
        
        material_row = table[table['Type'] == material_name]
        if material_row.empty:
            return JsonResponse({'status': 'error', 'message': 'Material not found'})
        
        m = material_row.iloc[0]
        
        # Calculate size factors
        if d_eff <= m['d_m_eff_N']:
            Kd_m = 1
        else:
            Kd_m = (1 - 0.7686 * m['ad_m'] * math.log(d_eff / 7.5, 10)) / (1 - 0.7686 * m['ad_m'] * math.log(m['d_p_eff_N'] / 7.5, 10))
        
        if d_eff <= m['d_p_eff_N']:
            Kd_p = 1
        else:
            Kd_p = (1 - 0.7686 * m['ad_p'] * math.log(d_eff / 7.5, 10)) / (1 - 0.7686 * m['ad_p'] * math.log(m['d_p_eff_N'] / 7.5, 10))
        
        # Anisotropy factor
        KA = [1, 0.9, 0.86, 0.83, 0.8][ka_index] if ka_index < 5 else 1
        
        # Fatigue strength factor
        fW_sigma = [0.4, 0.4, 0.45][fatigue_factor_index] if fatigue_factor_index < 3 else 0.4
        
        f_sigma = 1
        f_t = 0.577
        KT = 1
        
        Rm = m['Rm_N'] * Kd_m * KA
        Rp = m['Re_N'] * Kd_p * KA
        sigma_W_zd = fW_sigma * Rm
        t_W_s = f_t * sigma_W_zd
        
        results = [
            {'variable': 'Material', 'description': 'Material', 'value': material_name, 'ref': f'Table 5.1.{2 if material_type == "0" else 3}'},
            {'variable': 'Rm_N', 'description': 'Nominal Tensile Strength', 'value': round(float(m['Rm_N']), 3), 'ref': 'Table'},
            {'variable': 'Rp_N', 'description': 'Nominal Yield Strength', 'value': round(float(m['Re_N']), 3), 'ref': 'Table'},
            {'variable': 'ad_m', 'description': 'Material Constant (tensile)', 'value': round(float(m['ad_m']), 3), 'ref': 'Table'},
            {'variable': 'ad_p', 'description': 'Material Constant (yield)', 'value': round(float(m['ad_p']), 3), 'ref': 'Table'},
            {'variable': 'd_eff', 'description': 'Fabrication Effective Diameter', 'value': d_eff, 'ref': 'input'},
            {'variable': 'Kd_m', 'description': 'Technological Size Factor (tensile)', 'value': round(float(Kd_m), 3), 'ref': '3.2.1.4'},
            {'variable': 'Kd_p', 'description': 'Technological Size Factor (yield)', 'value': round(float(Kd_p), 3), 'ref': '3.2.1.4'},
            {'variable': 'KA', 'description': 'Anisotropy Factor', 'value': float(KA), 'ref': '3.2.1.5'},
            {'variable': 'fσ', 'description': 'Compression Strength Factor', 'value': float(f_sigma), 'ref': 'Table 3.2.5'},
            {'variable': 'ft', 'description': 'Shear Strength Factor', 'value': float(f_t), 'ref': 'Table 3.2.5'},
            {'variable': 'KT', 'description': 'Temperature Factor', 'value': float(KT), 'ref': '(3.2.20)'},
            {'variable': 'Rm', 'description': 'Standard Component Tensile Strength', 'value': round(float(Rm), 3), 'ref': '(3.2.1)'},
            {'variable': 'Rp', 'description': 'Standard Component Yield Strength', 'value': round(float(Rp), 3), 'ref': '(3.2.1)'},
            {'variable': 'fW,σ', 'description': 'Fatigue Strength Factor', 'value': float(fW_sigma), 'ref': 'Table 4.2.1'},
            {'variable': 'σW,zd', 'description': 'Characteristic Material Fatigue Limit', 'value': round(float(sigma_W_zd), 3), 'ref': '(4.2.1)'},
            {'variable': 'tW,s', 'description': 'Characteristic Shear Fatigue Limit', 'value': round(float(t_W_s), 3), 'ref': '(4.2.1)'},
        ]
        
        return JsonResponse({'status': 'success', 'results': results, 'material_data': {
            'Rm': float(Rm), 'Rp': float(Rp), 'sigma_W_zd': float(sigma_W_zd), 't_W_s': float(t_W_s),
            'A': float(m['A']), 'ad_m': float(m['ad_m']), 'ad_p': float(m['ad_p'])
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step3(request):
    """疲劳计算 - 步骤 3: 设计参数 (Base Material)"""
    try:
        data = json.loads(request.body)
        is_weld = data.get('is_weld', False)
        surface_treatment = float(data.get('surface_treatment', 1))
        roughness = float(data.get('roughness', 0))
        kt_calc_method = int(data.get('kt_calc_method', 0))
        
        # Material data from previous steps
        Rm = float(data.get('Rm', 500))
        sigma_W_zd = float(data.get('sigma_W_zd', 200))
        t_W_s = float(data.get('t_W_s', 115))
        A = float(data.get('A', 20))
        
        Kf = 2
        n_pl = 1
        K_V = surface_treatment
        K_S = 1
        K_NL_E = 1
        
        results = [
            {'variable': 'npl', 'description': 'Section Factor', 'value': n_pl, 'ref': 'per STD191010'},
            {'variable': 'Kf', 'description': 'Fatigue Notch Factor', 'value': Kf, 'ref': 'Table 4.3.1'},
            {'variable': 'Kv', 'description': 'Surface Treatment Factor', 'value': K_V, 'ref': 'Table 4.3.7' if K_V == 1 else '(4.3.28)'},
            {'variable': 'Ks', 'description': 'Coating Factor', 'value': K_S, 'ref': '(4.3.29)'},
            {'variable': 'KNL,E', 'description': 'Factor for GJL', 'value': K_NL_E, 'ref': '(4.3.32)'},
        ]
        
        # Roughness factor
        if roughness == 0:
            K_R_sigma = 1
            K_R_t = 1
            results.append({'variable': 'KR,σ', 'description': 'Roughness Factor (polished)', 'value': 1, 'ref': '(4.3.20)'})
            results.append({'variable': 'KR,t', 'description': 'Roughness Factor (polished)', 'value': 1, 'ref': '(4.3.20)'})
        else:
            Rz = roughness
            K_R_sigma = 1 - 0.22 * math.log(Rz, 10) * math.log(2 * Rm / 400, 10)
            K_R_t = 1 - 0.577 * 0.22 * math.log(Rz, 10) * math.log(2 * Rm / 400, 10)
            results.append({'variable': 'Rz', 'description': 'Surface Roughness', 'value': Rz, 'ref': 'input'})
            results.append({'variable': 'KR,σ', 'description': 'Roughness Factor', 'value': round(K_R_sigma, 3), 'ref': '(4.3.21)'})
            results.append({'variable': 'KR,t', 'description': 'Roughness Factor', 'value': round(K_R_t, 3), 'ref': '(4.3.21)'})
        
        # Kt-Kf ratio calculation - matching original PyQt script
        n_sigma = 1
        n_t = 1
        
        if kt_calc_method == 1:
            # Detailed calculation method - matching original PyQt script
            A_ref = 500
            A_sigma = float(data.get('A_sigma', 500))
            n_st = (A_ref / A_sigma) ** (1 / 30) if A_sigma > 0 else 1
            n_ = 0.15  # for steel
            
            ds = float(data.get('ds', 1))
            sigma_1a = float(data.get('sigma_1a', 100))
            t_1a = float(data.get('t_1a', 50))
            sigma_2a = float(data.get('sigma_2a', 80))
            t_2a = float(data.get('t_2a', 40))
            
            # Stress gradients
            G_s = abs(1 / ds * (1 - (sigma_2a / sigma_1a))) if sigma_1a != 0 else 0
            G_t = abs(1 / ds * (1 - (t_2a / t_1a))) if t_1a != 0 else 0
            
            # Deformation-mechanical factor
            n_vm = math.sqrt(1 + 210000 * 0.0002 / sigma_W_zd * (n_st ** (1 / n_ - 1))) if sigma_W_zd > 0 else 1
            
            # Fracture-mechanical factors
            n_bm_t = max(1, (5 + math.sqrt(G_t)) / (5 * n_vm * n_st + Rm / 680 * math.sqrt((7.5 + math.sqrt(G_t)) / 1 + 0.2 * math.sqrt(G_t))))
            n_bm_s = max(1, (5 + math.sqrt(G_s)) / (5 * n_vm * n_st + Rm / 680 * math.sqrt((7.5 + math.sqrt(G_s)) / 1 + 0.2 * math.sqrt(G_s))))
            
            n_sigma = n_st * n_vm * n_bm_s
            n_t = n_st * n_vm * n_bm_t
            
            results.extend([
                {'variable': 'n_st', 'description': 'Statistical Kt-Kf Ratio', 'value': round(n_st, 3), 'ref': '(4.3.11)'},
                {'variable': 'n_vm', 'description': 'Deformation-Mechanical Factor', 'value': round(n_vm, 3), 'ref': '(4.3.14)'},
                {'variable': 'n_bm,σ', 'description': 'Fracture-Mechanical Factor (normal)', 'value': round(n_bm_s, 3), 'ref': '(4.3.15)'},
                {'variable': 'n_bm,t', 'description': 'Fracture-Mechanical Factor (shear)', 'value': round(n_bm_t, 3), 'ref': '(4.3.15)'},
                {'variable': 'Gσ', 'description': 'Stress Gradient (normal)', 'value': round(G_s, 3), 'ref': 'calculation'},
                {'variable': 'Gt', 'description': 'Stress Gradient (shear)', 'value': round(G_t, 3), 'ref': 'calculation'},
            ])
        
        results.append({'variable': 'nσ', 'description': 'Material-Mechanical Kt-Kf Ratio', 'value': round(n_sigma, 3), 'ref': '(4.3.10)'})
        results.append({'variable': 'nt', 'description': 'Material-Mechanical Kt-Kf Ratio', 'value': round(n_t, 3), 'ref': '(4.3.10)'})
        
        # Design factors
        K_WK_sigma = 1 / n_sigma * (1 + 1 / Kf * (1 / K_R_sigma - 1)) / K_V / K_S / K_NL_E
        K_WK_t = 1 / n_t * (1 + 1 / Kf * (1 / K_R_t - 1)) / K_V / K_S
        
        results.append({'variable': 'Kwk,σ', 'description': 'Design Factor (normal)', 'value': round(K_WK_sigma, 3), 'ref': '(4.3.1)'})
        results.append({'variable': 'Kwk,t', 'description': 'Design Factor (shear)', 'value': round(K_WK_t, 3), 'ref': '(4.3.1)'})
        
        return JsonResponse({'status': 'success', 'results': results, 'step3_data': {
            'K_WK_sigma': K_WK_sigma, 'K_WK_t': K_WK_t, 'n_sigma': n_sigma, 'n_t': n_t, 'K_V': K_V, 'K_NL_E': K_NL_E
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step3_weld(request):
    """疲劳计算 - 步骤 3: 设计参数 (Welded Joint)"""
    try:
        data = json.loads(request.body)
        surface_treatment = float(data.get('surface_treatment', 1))
        roughness = float(data.get('roughness', 0))
        kt_calc_method = int(data.get('kt_calc_method', 0))
        a_W_index = int(data.get('a_W_index', 0))
        thickness_factor_exp_index = int(data.get('thickness_factor_exp_index', 0))
        d_eff = float(data.get('d_eff', 10))
        FAT_pp = float(data.get('FAT_pp', 100))
        FAT_pl = float(data.get('FAT_pl', 100))
        FAT_t = float(data.get('FAT_t', 100))
        material_name = data.get('material_name', data.get('material_type', 'S355'))
        
        # Material data from previous steps
        Rm = float(data.get('Rm', 500))
        Rp = float(data.get('Rp', 355))
        fW_t = 0.577
        
        Kf = 2
        n_pl = 1
        K_V = surface_treatment
        K_S = 1
        K_NL_E = 1
        
        results = [
            {'variable': 'npl', 'description': 'Section Factor', 'value': n_pl, 'ref': 'per STD191010'},
            {'variable': 'Kf', 'description': 'Fatigue Notch Factor', 'value': Kf, 'ref': 'Table 4.3.1'},
            {'variable': 'Kv', 'description': 'Surface Treatment Factor', 'value': K_V, 'ref': 'Table 4.3.7' if K_V == 1 else '(4.3.28)'},
            {'variable': 'Ks', 'description': 'Coating Factor', 'value': K_S, 'ref': '(4.3.29)'},
            {'variable': 'KNL,E', 'description': 'Factor for GJL', 'value': K_NL_E, 'ref': '(4.3.32)'},
        ]
        
        # Roughness factor
        if roughness == 0:
            K_R_sigma = 1
            K_R_t = 1
            results.append({'variable': 'KR,σ', 'description': 'Roughness Factor (polished)', 'value': 1, 'ref': '(4.3.20)'})
            results.append({'variable': 'KR,t', 'description': 'Roughness Factor (polished)', 'value': 1, 'ref': '(4.3.20)'})
        else:
            Rz = roughness
            K_R_sigma = 1 - 0.22 * math.log(Rz, 10) * math.log(2 * Rm / 400, 10)
            K_R_t = 1 - fW_t * 0.22 * math.log(Rz, 10) * math.log(2 * Rm / 400, 10)
            results.append({'variable': 'Rz', 'description': 'Surface Roughness', 'value': Rz, 'ref': 'input'})
            results.append({'variable': 'KR,σ', 'description': 'Roughness Factor', 'value': round(K_R_sigma, 3), 'ref': '(4.3.21)'})
            results.append({'variable': 'KR,t', 'description': 'Roughness Factor', 'value': round(K_R_t, 3), 'ref': '(4.3.21)'})
        
        # Kt-Kf ratio calculation (simplified for welds)
        n_sigma = 1
        n_t = 1
        results.append({'variable': 'nσ', 'description': 'Material-Mechanical Kt-Kf Ratio', 'value': 1, 'ref': '4.3.1.3'})
        results.append({'variable': 'nt', 'description': 'Material-Mechanical Kt-Kf Ratio', 'value': 1, 'ref': '4.3.1.3'})
        
        # Design factors
        K_WK_sigma = 1 / n_sigma * (1 + 1 / Kf * (1 / K_R_sigma - 1)) / K_V / K_S / K_NL_E
        K_WK_t = 1 / n_t * (1 + 1 / Kf * (1 / K_R_t - 1)) / K_V / K_S
        
        results.append({'variable': 'Kwk,σ', 'description': 'Design Factor (normal)', 'value': round(K_WK_sigma, 3), 'ref': '(4.3.1)'})
        results.append({'variable': 'Kwk,t', 'description': 'Design Factor (shear)', 'value': round(K_WK_t, 3), 'ref': '(4.3.1)'})
        
        # Weld factor a_W based on material and weld type - matching original PyQt script
        a_W = 1.0
        if a_W_index > 0:
            if 'S235' in material_name or 'S185' in material_name:
                a_W = 1.0 if a_W_index < 2 else 0.95
            elif 'S275' in material_name:
                a_W = 1.0 if a_W_index < 2 else 0.85
            elif 'S355' in material_name:
                a_W = 1.0 if a_W_index < 2 else 0.8
            elif 'S4' in material_name:
                a_W = 1.0 if a_W_index < 2 else 0.7
            elif 'S690' in material_name:
                a_W = 0.9 if a_W_index < 2 else 0.55
        
        results.append({'variable': 'aW', 'description': 'Weld Factor', 'value': a_W, 'ref': 'Table 3.3.5'})
        
        # Thickness factor exponent - matching original PyQt script
        n_exp = 0
        if thickness_factor_exp_index == 1:
            n_exp = 0.3
        elif thickness_factor_exp_index < 4:
            n_exp = 0.2
        elif thickness_factor_exp_index == 4:
            n_exp = 0.1
        
        # FAT factors - matching original PyQt script
        f_FAT_sigma = 0.5 * (2 / 5) ** (1 / 3)
        f_FAT_t = 0.5 * (2 / 100) ** 0.2
        
        # Thickness factor ft - matching original PyQt script
        if d_eff <= 25:
            ft = 1
        else:
            ft = (25 / d_eff) ** n_exp
        
        results.extend([
            {'variable': 'FAT⊥', 'description': 'FAT Class Perpendicular', 'value': FAT_pp, 'ref': 'Table 5.4.1'},
            {'variable': 'FAT∥', 'description': 'FAT Class Parallel', 'value': FAT_pl, 'ref': 'Table 5.4.3'},
            {'variable': 'FATt', 'description': 'FAT Class Shear', 'value': FAT_t, 'ref': 'Table 5.4.2'},
            {'variable': 'fFAT,σ', 'description': 'Factor for FAT Class', 'value': round(f_FAT_sigma, 3), 'ref': 'Table 4.4.3'},
            {'variable': 'fFAT,t', 'description': 'Factor for FAT Class', 'value': round(f_FAT_t, 3), 'ref': 'Table 4.4.3'},
            {'variable': 'ft', 'description': 'Thickness Factor', 'value': round(ft, 3), 'ref': '(4.3.24)' if d_eff > 25 else '(4.3.23)'},
        ])
        
        return JsonResponse({'status': 'success', 'results': results, 'step3_data': {
            'K_WK_sigma': K_WK_sigma, 'K_WK_t': K_WK_t, 'n_sigma': n_sigma, 'n_t': n_t,
            'a_W': a_W, 'ft': ft, 'f_FAT_sigma': f_FAT_sigma, 'f_FAT_t': f_FAT_t,
            'FAT_pp': FAT_pp, 'FAT_pl': FAT_pl, 'FAT_t': FAT_t, 'K_V': K_V, 'K_NL_E': K_NL_E
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step4(request):
    """疲劳计算 - 步骤 4: 组件强度 (Base Material)"""
    try:
        data = json.loads(request.body)
        
        # Get data from previous steps
        sigma_W_zd = float(data.get('sigma_W_zd', 200))
        t_W_s = float(data.get('t_W_s', 115))
        K_WK_sigma = float(data.get('K_WK_sigma', 1))
        K_WK_t = float(data.get('K_WK_t', 1))
        Rm = float(data.get('Rm', 500))
        Rp = float(data.get('Rp', 355))
        n_pl = float(data.get('n_pl', 1))
        f_t = 0.577
        
        # Stress ratios from step 1
        Rx = float(data.get('Rx', 0))
        Ry = float(data.get('Ry', 0))
        Rt = float(data.get('Rt', 0))
        sigma_m_x = float(data.get('sigma_m_x', 0))
        sigma_a_x = float(data.get('sigma_a_x', 0))
        sigma_m_y = float(data.get('sigma_m_y', 0))
        sigma_a_y = float(data.get('sigma_a_y', 0))
        t_m = float(data.get('t_m', 0))
        t_a = float(data.get('t_a', 0))
        
        # Component fatigue limits
        sigma_WK = sigma_W_zd / K_WK_sigma
        t_WK = t_W_s / K_WK_t
        
        # Mean stress sensitivity
        a_M = 0.35
        b_M = -0.1
        M_sigma = a_M * 0.001 * Rm + b_M
        M_t = f_t * M_sigma
        
        # Residual stress factors
        K_E_sigma = 1
        K_E_t = 1
        
        results = [
            {'variable': 'σWK', 'description': 'Component Fatigue Limit (normal)', 'value': round(sigma_WK, 3), 'ref': '(4.4.1)'},
            {'variable': 'tWK', 'description': 'Component Fatigue Limit (shear)', 'value': round(t_WK, 3), 'ref': '(4.4.1)'},
            {'variable': 'Mσ', 'description': 'Mean Stress Sensitivity', 'value': round(M_sigma, 3), 'ref': '(4.4.5)'},
            {'variable': 'Mt', 'description': 'Mean Stress Sensitivity (shear)', 'value': round(M_t, 3), 'ref': '(4.4.5)'},
        ]
        
        # Mean stress factors
        def calc_K_AK(R, M, sigma_m, sigma_a):
            if R > 1:
                return 1 / (1 - M)
            elif R <= 0:
                if sigma_a == 0:
                    return 1
                return 1 / (1 + M * sigma_m / sigma_a)
            elif R < 0.5:
                if sigma_a == 0:
                    return (3 + M) / (1 + M) / 3
                return (3 + M) / (1 + M) / (3 + M * sigma_m / sigma_a)
            else:
                return (3 + M) / 3 / (1 + M) ** 2
        
        K_AK_x = calc_K_AK(Rx, M_sigma, sigma_m_x, sigma_a_x)
        K_AK_y = calc_K_AK(Ry, M_sigma, sigma_m_y, sigma_a_y)
        K_AK_t = calc_K_AK(Rt, M_t, t_m, t_a)
        
        sigma_AK_x = K_AK_x * sigma_WK
        sigma_AK_y = K_AK_y * sigma_WK
        t_AK = K_AK_t * t_WK
        
        results.extend([
            {'variable': 'K_AK,x', 'description': 'Mean Stress Factor (X)', 'value': round(K_AK_x, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'K_AK,y', 'description': 'Mean Stress Factor (Y)', 'value': round(K_AK_y, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'K_AK,t', 'description': 'Mean Stress Factor (shear)', 'value': round(K_AK_t, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'σAK,x', 'description': 'Amplitude of Component Fatigue Limit (X)', 'value': round(sigma_AK_x, 3), 'ref': '(4.4.4)'},
            {'variable': 'σAK,y', 'description': 'Amplitude of Component Fatigue Limit (Y)', 'value': round(sigma_AK_y, 3), 'ref': '(4.4.4)'},
            {'variable': 'tAK', 'description': 'Amplitude of Component Fatigue Limit (shear)', 'value': round(t_AK, 3), 'ref': '(4.4.4)'},
        ])
        
        # N_bar and fatigue strength factor
        N_bar = float(data.get('N_bar', 1))
        ND_sigma = 1
        ND_t = 1
        
        if N_bar >= 1:
            K_BK_n = 1
            K_BK_t = 1
        else:
            K_BK_n = (1 / N_bar) ** 0.2
            K_BK_t = (1 / N_bar) ** 0.125
        
        sigma_BK_max = 0.75 * Rp * n_pl
        t_BK_max = 0.75 * f_t * Rp * n_pl
        
        if sigma_BK_max > K_BK_n * sigma_AK_x:
            sigma_BK_x = K_BK_n * sigma_AK_x
        else:
            sigma_BK_x = sigma_BK_max
        
        if sigma_BK_max > K_BK_n * sigma_AK_y:
            sigma_BK_y = K_BK_n * sigma_AK_y
        else:
            sigma_BK_y = sigma_BK_max
        
        if t_BK_max > K_BK_t * t_AK:
            t_BK = K_BK_t * t_AK
        else:
            t_BK = t_BK_max
        
        results.extend([
            {'variable': 'N_D,σ', 'description': 'Number of Cycles at Knee Point', 'value': int(ND_sigma * 1e6), 'ref': 'Table 4.4.3'},
            {'variable': 'N_D,t', 'description': 'Number of Cycles at Knee Point', 'value': int(ND_t * 1e6), 'ref': 'Table 4.4.4'},
            {'variable': 'kσ', 'description': 'Slope Exponent', 'value': 5, 'ref': '(4.4.40)'},
            {'variable': 'kt', 'description': 'Slope Exponent', 'value': 8, 'ref': '(4.4.40)'},
            {'variable': 'N', 'description': 'Required Cycles', 'value': int(N_bar * 1e6), 'ref': 'per design'},
            {'variable': 'K_BK,n', 'description': 'Variable Amplitude Factor', 'value': round(K_BK_n, 3), 'ref': '(4.4.38)'},
            {'variable': 'K_BK,t', 'description': 'Variable Amplitude Factor', 'value': round(K_BK_t, 3), 'ref': '(4.4.38)'},
            {'variable': 'σBK,max', 'description': 'Max Variable Amplitude Strength', 'value': round(sigma_BK_max, 3), 'ref': '(4.4.38)'},
            {'variable': 'tBK,max', 'description': 'Max Variable Amplitude Strength', 'value': round(t_BK_max, 3), 'ref': '(4.4.38)'},
            {'variable': 'σBK,x', 'description': 'Variable Amplitude Strength (X)', 'value': round(sigma_BK_x, 3), 'ref': '(4.4.38)'},
            {'variable': 'σBK,y', 'description': 'Variable Amplitude Strength (Y)', 'value': round(sigma_BK_y, 3), 'ref': '(4.4.38)'},
            {'variable': 'tBK', 'description': 'Variable Amplitude Strength (shear)', 'value': round(t_BK, 3), 'ref': '(4.4.38)'},
        ])
        
        return JsonResponse({'status': 'success', 'results': results, 'step4_data': {
            'sigma_BK_x': sigma_BK_x, 'sigma_BK_y': sigma_BK_y, 't_BK': t_BK,
            'sigma_AK_x': sigma_AK_x, 'sigma_AK_y': sigma_AK_y, 't_AK': t_AK
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step4_weld(request):
    """疲劳计算 - 步骤 4: 组件强度 (Welded Joint)"""
    try:
        data = json.loads(request.body)
        
        # Get data from step 3 weld
        FAT_pp = float(data.get('FAT_pp', 100))
        FAT_pl = float(data.get('FAT_pl', 100))
        FAT_t = float(data.get('FAT_t', 100))
        ft = float(data.get('ft', 1))
        K_V = float(data.get('K_V', 1))
        K_NL_E = float(data.get('K_NL_E', 1))
        a_W = float(data.get('a_W', 1))
        f_FAT_sigma = float(data.get('f_FAT_sigma', 0.368))
        f_FAT_t = float(data.get('f_FAT_t', 0.231))
        
        # Residual stress condition
        sel_KE = int(data.get('sel_KE', 0))
        
        if sel_KE == 0:
            K_E_sigma = 1
            M_sigma = 0
            K_E_t = 1
            M_t = 0
        elif sel_KE == 1:
            K_E_sigma = 1.26
            M_sigma = 0.15
            K_E_t = 1.15
            M_t = 0.09
        else:
            K_E_sigma = 1.54
            M_sigma = 0.3
            K_E_t = 1.3
            M_t = 0.17
        
        results = [
            {'variable': 'KE,σ', 'description': 'Residual Stress Factor', 'value': K_E_sigma, 'ref': 'Table 4.4.2'},
            {'variable': 'Mσ', 'description': 'Mean Stress Sensitivity', 'value': M_sigma, 'ref': 'Table 4.4.2'},
            {'variable': 'KE,t', 'description': 'Residual Stress Factor', 'value': K_E_t, 'ref': 'Table 4.4.2'},
            {'variable': 'Mt', 'description': 'Mean Stress Sensitivity', 'value': M_t, 'ref': 'Table 4.4.2'},
        ]
        
        # Component fatigue limits for welds
        sigma_WK_pp = FAT_pp * f_FAT_sigma * ft * K_V * K_NL_E
        sigma_WK_pl = FAT_pl * f_FAT_sigma * ft * K_V * K_NL_E
        t_WK = FAT_t * f_FAT_t * ft * K_V
        
        results.extend([
            {'variable': 'σWK,⊥', 'description': 'Component Fatigue Limit (perp)', 'value': round(sigma_WK_pp, 3), 'ref': '(4.4.2)'},
            {'variable': 'σWK,∥', 'description': 'Component Fatigue Limit (parallel)', 'value': round(sigma_WK_pl, 3), 'ref': '(4.4.2)'},
            {'variable': 'tWK', 'description': 'Component Fatigue Limit (shear)', 'value': round(t_WK, 3), 'ref': '(4.4.2)'},
        ])
        
        # Stress ratios from step 1 weld
        R_pp = float(data.get('R_pp', 0))
        R_pl = float(data.get('R_pl', 0))
        R_t = float(data.get('R_t', 0))
        sigma_m_n = float(data.get('sigma_m_n', 0))
        sigma_a_n = float(data.get('sigma_a_n', 0))
        sigma_m_1 = float(data.get('sigma_m_1', 0))
        sigma_a_1 = float(data.get('sigma_a_1', 0))
        t_m_1 = float(data.get('t_m_1', 0))
        t_a_1 = float(data.get('t_a_1', 0))
        
        # Mean stress factors
        def calc_K_AK(R, M, sigma_m, sigma_a):
            if R > 1:
                return 1 / (1 - M)
            elif R <= 0:
                if sigma_a == 0:
                    return 1
                return 1 / (1 + M * sigma_m / sigma_a)
            elif R < 0.5:
                if sigma_a == 0:
                    return (3 + M) / (1 + M) / 3
                return (3 + M) / (1 + M) / (3 + M * sigma_m / sigma_a)
            else:
                return (3 + M) / 3 / (1 + M) ** 2
        
        K_AK_pp = calc_K_AK(R_pp, M_sigma, sigma_m_n, sigma_a_n)
        K_AK_pl = calc_K_AK(R_pl, M_sigma, sigma_m_1, sigma_a_1)
        K_AK_t = calc_K_AK(R_t, M_t, t_m_1, t_a_1)
        
        sigma_AK_pp = K_AK_pp * K_E_sigma * sigma_WK_pp
        sigma_AK_pl = K_AK_pl * K_E_sigma * sigma_WK_pl
        t_AK = K_AK_t * K_E_t * t_WK
        
        results.extend([
            {'variable': 'K_AK,⊥', 'description': 'Mean Stress Factor (perp)', 'value': round(K_AK_pp, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'K_AK,∥', 'description': 'Mean Stress Factor (parallel)', 'value': round(K_AK_pl, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'K_AK,t', 'description': 'Mean Stress Factor (shear)', 'value': round(K_AK_t, 3), 'ref': '(4.4.8-11)'},
            {'variable': 'σAK,⊥', 'description': 'Amplitude of Component Fatigue Limit', 'value': round(sigma_AK_pp, 3), 'ref': '(4.4.41)'},
            {'variable': 'σAK,∥', 'description': 'Amplitude of Component Fatigue Limit', 'value': round(sigma_AK_pl, 3), 'ref': '(4.4.41)'},
            {'variable': 'tAK', 'description': 'Amplitude of Component Fatigue Limit', 'value': round(t_AK, 3), 'ref': '(4.4.41)'},
        ])
        
        # N_bar and fatigue strength factor for welds
        N_bar = float(data.get('N_bar', 1))
        ND_sigma = 5
        ND_t = 100
        k_sigma = 3
        k_t = 5
        
        if N_bar >= ND_sigma:
            K_BK_n = 1
        else:
            K_BK_n = (ND_sigma / N_bar) ** (1 / k_sigma)
        
        if N_bar >= ND_t:
            K_BK_t = 1
        else:
            K_BK_t = (ND_t / N_bar) ** (1 / k_t)
        
        sigma_BK_max = 0.75 * float(data.get('Rp', 355)) * float(data.get('n_pl', 1)) * a_W
        t_BK_max = sigma_BK_max  # Same for welds
        
        if sigma_BK_max > K_BK_n * sigma_AK_pp:
            sigma_BK_pp = K_BK_n * sigma_AK_pp
        else:
            sigma_BK_pp = sigma_BK_max
        
        if sigma_BK_max > K_BK_n * sigma_AK_pl:
            sigma_BK_pl = K_BK_n * sigma_AK_pl
        else:
            sigma_BK_pl = sigma_BK_max
        
        if t_BK_max > K_BK_t * t_AK:
            t_BK = K_BK_t * t_AK
        else:
            t_BK = t_BK_max
        
        results.extend([
            {'variable': 'N_D,σ', 'description': 'Number of Cycles at Knee Point', 'value': int(ND_sigma * 1e6), 'ref': '(4.4.39)'},
            {'variable': 'N_D,t', 'description': 'Number of Cycles at Knee Point', 'value': int(ND_t * 1e6), 'ref': '(4.4.39)'},
            {'variable': 'kσ', 'description': 'Slope Exponent', 'value': k_sigma, 'ref': '(4.4.39)'},
            {'variable': 'kt', 'description': 'Slope Exponent', 'value': k_t, 'ref': '(4.4.39)'},
            {'variable': 'N', 'description': 'Required Cycles', 'value': int(N_bar * 1e6), 'ref': 'per design'},
            {'variable': 'K_BK,⊥', 'description': 'Variable Amplitude Factor', 'value': round(K_BK_n, 3), 'ref': '(4.4.41)'},
            {'variable': 'K_BK,∥', 'description': 'Variable Amplitude Factor', 'value': round(K_BK_n, 3), 'ref': '(4.4.41)'},
            {'variable': 'K_BK,t', 'description': 'Variable Amplitude Factor', 'value': round(K_BK_t, 3), 'ref': '(4.4.41)'},
            {'variable': 'σBK,max', 'description': 'Max Variable Amplitude Strength', 'value': round(sigma_BK_max, 3), 'ref': '(4.4.41)'},
            {'variable': 'tBK,max', 'description': 'Max Variable Amplitude Strength', 'value': round(t_BK_max, 3), 'ref': '(4.4.41)'},
            {'variable': 'σBK,⊥', 'description': 'Variable Amplitude Strength (perp)', 'value': round(sigma_BK_pp, 3), 'ref': '(4.4.41)'},
            {'variable': 'σBK,∥', 'description': 'Variable Amplitude Strength (parallel)', 'value': round(sigma_BK_pl, 3), 'ref': '(4.4.41)'},
            {'variable': 'tBK', 'description': 'Variable Amplitude Strength (shear)', 'value': round(t_BK, 3), 'ref': '(4.4.41)'},
        ])
        
        return JsonResponse({'status': 'success', 'results': results, 'step4_data': {
            'sigma_BK_pp': sigma_BK_pp, 'sigma_BK_pl': sigma_BK_pl, 't_BK': t_BK,
            'sigma_AK_pp': sigma_AK_pp, 'sigma_AK_pl': sigma_AK_pl, 't_AK': t_AK
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step5(request):
    """疲劳计算 - 步骤 5: 安全系数"""
    try:
        data = json.loads(request.body)
        
        consequence = int(data.get('consequence', 1))
        inspection = int(data.get('inspection', 1))
        jG_index = int(data.get('jG_index', 0))
        is_weld = data.get('is_weld', False)
        
        j_S = 1
        K_t_D = 1
        
        # Safety factors based on consequence and inspection
        if is_weld:
            j_F_values = {
                (0, 0): 1.4, (0, 1): 1.2,
                (1, 0): 1.25, (1, 1): 1.1,
                (2, 0): 1.15, (2, 1): 1.0
            }
        else:
            j_F_values = {
                (0, 0): 1.5, (0, 1): 1.35,
                (1, 0): 1.4, (1, 1): 1.25,
                (2, 0): 1.3, (2, 1): 1.2
            }
        
        j_F = j_F_values.get((consequence, inspection), 1.25)
        jG = [1, 1, 1.25, 1.4][jG_index] if jG_index < 4 else 1
        j_D = j_S * j_F * jG / K_t_D
        
        consequence_labels = ['Severe', 'Mean', 'Moderate']
        inspection_labels = ['No', 'Yes']
        
        results = [
            {'variable': 'jS', 'description': 'Load Safety Factor', 'value': j_S, 'ref': '(4.5.1)'},
            {'variable': '', 'description': 'Consequence of Failure', 'value': consequence_labels[consequence], 'ref': ''},
            {'variable': '', 'description': 'Regular Inspections', 'value': inspection_labels[inspection], 'ref': ''},
            {'variable': 'jF', 'description': 'Material Safety Factor', 'value': j_F, 'ref': 'Table 4.5.1'},
            {'variable': 'jG', 'description': 'Casting Factor', 'value': jG, 'ref': 'Table 4.5.2'},
            {'variable': 'KT,D', 'description': 'Temperature Factor', 'value': K_t_D, 'ref': 'Normal Temperature'},
            {'variable': 'jD', 'description': 'Total Safety Factor', 'value': round(j_D, 3), 'ref': '(4.5.2)'},
        ]
        
        return JsonResponse({'status': 'success', 'results': results, 'j_D': j_D})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_fatigue_step6(request):
    """疲劳计算 - 步骤 6: 评估"""
    try:
        data = json.loads(request.body)
        is_weld = data.get('is_weld', False)
        
        if not is_weld:
            # Base material assessment
            sigma_a_x = float(data.get('sigma_a_x', 0))
            sigma_a_y = float(data.get('sigma_a_y', 0))
            t_a = float(data.get('t_a', 0))
            j_D = float(data.get('j_D', 1))
            sigma_BK_x = float(data.get('sigma_BK_x', 100))
            sigma_BK_y = float(data.get('sigma_BK_y', 100))
            t_BK = float(data.get('t_BK', 100))
            
            a_BK_sigma_x = sigma_a_x * j_D / sigma_BK_x if sigma_BK_x > 0 else 0
            a_BK_sigma_y = sigma_a_y * j_D / sigma_BK_y if sigma_BK_y > 0 else 0
            a_BK_t = t_a * j_D / t_BK if t_BK > 0 else 0
            a_BK_sigma_v = math.sqrt(a_BK_sigma_x**2 + a_BK_sigma_y**2 - a_BK_sigma_x*a_BK_sigma_y + a_BK_t**2)
            
            results = [
                {'variable': 'aBK,σx', 'description': 'DOU for Normal Stress X', 'value': round(a_BK_sigma_x, 3), 'ref': '(4.6.3)'},
                {'variable': 'aBK,σy', 'description': 'DOU for Normal Stress Y', 'value': round(a_BK_sigma_y, 3), 'ref': '(4.6.3)'},
                {'variable': 'aBK,t', 'description': 'DOU for Shear Stress', 'value': round(a_BK_t, 3), 'ref': '(4.6.3)'},
                {'variable': 'aBK,σv', 'description': 'DOU for Combined Stress', 'value': round(a_BK_sigma_v, 3), 'ref': '(4.6.10)'},
            ]
        else:
            # Weld assessment
            sigma_a_n = float(data.get('sigma_a_n', 0))
            sigma_a_1 = float(data.get('sigma_a_1', 0))
            t_a_1 = float(data.get('t_a_1', 0))
            j_D = float(data.get('j_D', 1))
            sigma_BK_pp = float(data.get('sigma_BK_pp', 100))
            sigma_BK_pl = float(data.get('sigma_BK_pl', 100))
            t_BK = float(data.get('t_BK', 100))
            
            a_BK_sigma_pp = sigma_a_n * j_D / sigma_BK_pp if sigma_BK_pp > 0 else 0
            a_BK_sigma_pl = sigma_a_1 * j_D / sigma_BK_pl if sigma_BK_pl > 0 else 0
            a_BK_t = t_a_1 * j_D / t_BK if t_BK > 0 else 0
            a_BK_v = 0.5 * (abs(a_BK_sigma_pp + a_BK_sigma_pl) + math.sqrt((a_BK_sigma_pl - a_BK_sigma_pp)**2 + 4*a_BK_t**2))
            
            results = [
                {'variable': 'aBK,⊥', 'description': 'DOU for Normal Stress Perpendicular', 'value': round(a_BK_sigma_pp, 3), 'ref': '(4.6.4)'},
                {'variable': 'aBK,∥', 'description': 'DOU for Normal Stress Parallel', 'value': round(a_BK_sigma_pl, 3), 'ref': '(4.6.4)'},
                {'variable': 'aBK,t', 'description': 'DOU for Shear Stress', 'value': round(a_BK_t, 3), 'ref': '(4.6.4)'},
                {'variable': 'aBK,σv', 'description': 'DOU for Combined Stress', 'value': round(a_BK_v, 3), 'ref': '(4.6.13)'},
            ]
        
        assessment = "PASS" if results[-1]['value'] <= 1.0 else "FAIL"
        
        return JsonResponse({'status': 'success', 'results': results, 'assessment': assessment})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


from django.http import HttpResponse

@csrf_exempt
def export_fatigue_report(request):
    """导出疲劳计算报告为 Excel 文件"""
    try:
        data = json.loads(request.body)
        is_weld = data.get('is_weld', False)
        steps = data.get('steps', [])
        
        # Step names matching original script
        step_names = [
            'Step 1: Characteristic Service Stresses',
            'Step 2: Material Properties',
            'Step 3: Design Parameters',
            'Step 4: Component Strength',
            'Step 5: Safety Factors',
            'Step 6: Assessment'
        ]
        
        # Build data list with separator rows and step headers
        all_rows = []
        for i, step_data in enumerate(steps):
            step_name = step_data.get('step_name', step_names[i] if i < len(step_names) else f'Step {i+1}')
            variables = step_data.get('variables', [])
            
            # Add empty separator row
            all_rows.append(['', '', '', ''])
            
            # Add step header row
            all_rows.append([step_name, '', '', ''])
            
            # Add variable rows
            for var in variables:
                all_rows.append([
                    var.get('variable', ''),
                    var.get('description', ''),
                    var.get('value', ''),
                    var.get('ref', '')
                ])
        
        # Calculate row positions for merging
        format_list = [0] * 7
        current_row = 0
        for i, step_data in enumerate(steps):
            variables = step_data.get('variables', [])
            format_list[i] = current_row + 1  # Header row position (1-indexed in xlsxwriter)
            current_row += 2 + len(variables)  # separator + header + variables
        
        # Create Excel file using xlsxwriter directly
        output = io.BytesIO()
        
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sheet1')
        
        # Add formats - matching original script
        format_bgc = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center'})
        format_bgc.set_center_across()
        format1 = workbook.add_format({'num_format': '#,##0.000', 'align': 'center'})
        
        # Write data to worksheet
        for row_idx, row_data in enumerate(all_rows):
            for col_idx, cell_value in enumerate(row_data):
                worksheet.write(row_idx, col_idx, cell_value)
        
        # Set column widths: A=10, B=45, C-D=16
        worksheet.set_column(0, 0, 10, format1)
        worksheet.set_column(1, 1, 45)
        worksheet.set_column(2, 3, 16, format1)
        
        # Merge step header rows - only for steps that have data
        for i, step_name in enumerate(step_names):
            if i < len(steps) and format_list[i] > 0:
                row = format_list[i]
                worksheet.merge_range(row, 0, row, 3, step_name, format_bgc)
        
        workbook.close()
        
        output.seek(0)
        filename = f"fatigue_{'welded' if is_weld else 'non_welded'}_{date.today().strftime('%Y-%m-%d')}.xlsx"
        
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except Exception as e:
        import traceback
        return JsonResponse({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()})


def convert_to_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    import numpy as np
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    return obj


@csrf_exempt
def calculate_static_step1(request):
    """静强度计算 - 步骤 1: 特征服务应力"""
    try:
        data = json.loads(request.body)
        calculation_type = data.get('calculation_type', 'base')
        
        if calculation_type == 'base':
            sigma_vm = float(data.get('sigma_vm', 0))
            sigma_x = float(data.get('sigma_x', 0))
            sigma_y = float(data.get('sigma_y', 0))
            sigma_z = float(data.get('sigma_z', 0))
            
            sigma_h = 1/3 * (sigma_x + sigma_y + sigma_z)
            h = sigma_h / sigma_vm if sigma_vm > 0 else 0
            
            results = [
                {'variable': 'σvm', 'description': 'Max Von-Mises Stress', 'value': float(sigma_vm), 'ref': 'input'},
                {'variable': 'σx', 'description': 'X Normal Stress', 'value': float(sigma_x), 'ref': 'input'},
                {'variable': 'σy', 'description': 'Y Normal Stress', 'value': float(sigma_y), 'ref': 'input'},
                {'variable': 'σz', 'description': 'Z Normal Stress', 'value': float(sigma_z), 'ref': 'input'},
                {'variable': 'σh', 'description': 'Hydrostatic Stress', 'value': round(float(sigma_h), 3), 'ref': '(3.1.11)'},
                {'variable': 'h', 'description': 'Degree of Multiaxiality', 'value': round(float(h), 3), 'ref': '(3.1.10)'},
            ]
        else:
            sigma_n = float(data.get('sigma_n', 0))
            t_l = float(data.get('t_l', 0))
            
            sigma_vm_w = math.sqrt(sigma_n ** 2 + 3 * t_l ** 2)
            
            results = [
                {'variable': 'σn', 'description': 'Normal Stress Perpendicular to Welds', 'value': float(sigma_n), 'ref': 'input'},
                {'variable': 't_l', 'description': 'Shear Stress Parallel to Welds', 'value': float(t_l), 'ref': 'input'},
                {'variable': 'σvm_w', 'description': 'Equivalent Stress at Welds', 'value': round(float(sigma_vm_w), 3), 'ref': '3.1.14 (modified by STD191010)'},
            ]
        
        return JsonResponse({'status': 'success', 'results': results})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_static_step3(request):
    """静强度计算 - 步骤 3: 设计参数"""
    try:
        data = json.loads(request.body)
        npl_method = int(data.get('npl_method', 0))
        surface_hardening = int(data.get('surface_hardening', 0))
        h = float(data.get('h', 0))
        Rp = float(data.get('Rp', 235))
        A = float(data.get('A', 20))
        
        epsilon_ref = A / 100
        epsilon_0 = 0.05
        E = 210000  # MPa
        
        results = []
        n_pl = 1
        Kp_b = 1
        Kp_t = 1
        
        if npl_method == 0:
            # Conservative method
            results = [
                {'variable': 'n_pl', 'description': 'Section Factor', 'value': 1, 'ref': '3.3.1.1'},
                {'variable': 'Kp_b', 'description': 'Plastic Notch Factor (bending)', 'value': 1, 'ref': 'Conservative'},
                {'variable': 'Kp_t', 'description': 'Plastic Notch Factor (torsion)', 'value': 1, 'ref': 'Conservative'},
            ]
        else:
            # Consider plastic reserve
            cross_section_type = int(data.get('cross_section_type', 0))
            
            if cross_section_type == 0:
                Kp_b = 1.5
                Kp_t = 'N/A'
            elif cross_section_type == 1:
                Kp_b = 1.7
                Kp_t = 1.33
            elif cross_section_type == 2:
                d = float(data.get('id', 80))
                D = float(data.get('od', 100))
                Kp_b = 1.27
                Kp_t = 1.33 * (1 - (d / D) ** 3) / (1 - (d / D) ** 4)
            elif cross_section_type == 3:
                b = float(data.get('iw', 80))
                B = float(data.get('ow', 100))
                h_sec = float(data.get('ih', 160))
                H = float(data.get('oh', 200))
                Kp_b = 1.5 * (1 - b / B * (h_sec / H) ** 2) / (1 - b / B * (h_sec / H) ** 3)
                Kp_t = 'N/A'
            
            # Calculate epsilon_ertr
            if surface_hardening == 1:
                epsilon_ertr = 0.01
            else:
                if h <= 1/3:
                    epsilon_ertr = epsilon_ref
                else:
                    epsilon_ertr = epsilon_0 + 0.3 * ((epsilon_ref - 0.05) / 0.3) ** (3 * h)
            
            # Calculate Kp
            if Kp_t == 'N/A':
                Kp = Kp_b
            elif Kp_b == 'N/A':
                Kp = Kp_t
            else:
                Kp = min(Kp_b, Kp_t)
            
            n_pl = min(math.sqrt(E * epsilon_ertr / Rp), Kp)
            
            results = [
                {'variable': 'n_pl', 'description': 'Section Factor', 'value': round(n_pl, 3), 'ref': '(3.3.2)'},
                {'variable': 'Kp_b', 'description': 'Plastic Notch Factor (bending)', 'value': Kp_b if Kp_b != 'N/A' else 'N/A', 'ref': 'Table 1.3.2'},
                {'variable': 'Kp_t', 'description': 'Plastic Notch Factor (torsion)', 'value': Kp_t if Kp_t != 'N/A' else 'N/A', 'ref': 'Table 1.3.2'},
                {'variable': 'E', 'description': "Young's Modulus", 'value': E, 'ref': 'Material'},
                {'variable': 'ε_entr', 'description': 'Critical Total Strain', 'value': round(epsilon_ertr, 4), 'ref': '(3.3.3)'},
                {'variable': 'ε_0', 'description': 'Min Critical Strain', 'value': epsilon_0, 'ref': 'Table 3.3.1'},
                {'variable': 'ε_ref', 'description': 'Reference Strain', 'value': epsilon_ref, 'ref': '(3.3.4)'},
            ]
        
        # Weld factor
        a_W = 1.0
        if data.get('a_W_index'):
            a_W_index = int(data.get('a_W_index', 0))
            material_name = data.get('material_name', '')
            if a_W_index > 0:
                if 'S235' in material_name or 'S185' in material_name:
                    a_W = 1.0 if a_W_index < 2 else 0.95
                elif 'S275' in material_name:
                    a_W = 1.0 if a_W_index < 2 else 0.85
                elif 'S355' in material_name:
                    a_W = 1.0 if a_W_index < 2 else 0.8
                elif 'S4' in material_name:
                    a_W = 1.0 if a_W_index < 2 else 0.7
                elif 'S690' in material_name:
                    a_W = 0.9 if a_W_index < 2 else 0.55
            
            results.append({'variable': 'a_W', 'description': 'Weld Factor', 'value': a_W, 'ref': 'Table 3.3.5'})
        
        return JsonResponse({'status': 'success', 'results': results, 'step3_data': {
            'n_pl': n_pl, 'Kp_b': Kp_b, 'Kp_t': Kp_t, 'a_W': a_W
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_static_step4(request):
    """静强度计算 - 步骤 4: 组件强度 (Base Material)"""
    try:
        data = json.loads(request.body)
        Rp = float(data.get('Rp', 235))
        n_pl = float(data.get('n_pl', 1))
        
        sigma_SK = Rp * n_pl
        
        results = [
            {'variable': 'σSK', 'description': 'Component Strength', 'value': round(sigma_SK, 3), 'ref': '(3.4.1)'},
        ]
        
        return JsonResponse({'status': 'success', 'results': results, 'step4_data': {'sigma_SK': sigma_SK}})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_static_step4_weld(request):
    """静强度计算 - 步骤 4: 组件强度 (Welded Joint)"""
    try:
        data = json.loads(request.body)
        material_name = data.get('material_name', 'S235')
        material_type = data.get('material_type', '0')
        d_eff = float(data.get('d_eff', 10))
        n_pl = float(data.get('n_pl', 1))
        a_W = float(data.get('a_W', 1))
        Rp = float(data.get('Rp', 235))
        Rm = float(data.get('Rm', 360))
        
        # Read from Excel Table 5.1.24
        excel_path = os.path.join(FKM_DIR, 'FKM Structural Steel.xlsx')
        sheet_name = 'Table 5.1.24 SS' if material_type == '0' else 'Table 5.1.24 FG'
        
        try:
            table = pd.read_excel(excel_path, sheet_name=sheet_name)
            
            # Find matching row based on d_eff and material_name
            if d_eff <= 40:
                temp = table[table['t'] == 40]
            else:
                temp = table[table['t'] > 40]
            temp = temp[temp['Material Type'] == material_name]
            
            if not temp.empty:
                Re = float(temp['Re'].values[0])
                Rm_weld = float(temp['Rm'].values[0])
            else:
                # Fallback values
                Re = Rp * 0.8
                Rm_weld = Rm * 0.8
        except:
            Re = Rp * 0.8
            Rm_weld = Rm * 0.8
        
        sigma_SK_BM_HAZ = Re * n_pl
        sigma_SK_w = Re * n_pl * a_W
        
        results = [
            {'variable': 'Re_weld', 'description': 'Material Yield Strength (weld)', 'value': round(Re, 3), 'ref': 'Table 5.1.24'},
            {'variable': 'Rm_weld', 'description': 'Material Tensile Strength (weld)', 'value': round(Rm_weld, 3), 'ref': 'Table 5.1.24'},
            {'variable': 'σSK,BM/HAZ', 'description': 'Component Strength (BM/HAZ)', 'value': round(sigma_SK_BM_HAZ, 3), 'ref': '(3.4.2)'},
            {'variable': 'σSK,W', 'description': 'Component Strength at Welds', 'value': round(sigma_SK_w, 3), 'ref': '(3.4.4)'},
        ]
        
        return JsonResponse({'status': 'success', 'results': results, 'step4_data': {
            'sigma_SK': sigma_SK_BM_HAZ, 'sigma_SK_w': sigma_SK_w, 'Re_weld': Re, 'Rm_weld': Rm_weld
        }})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_static_step5(request):
    """静强度计算 - 步骤 5: 安全系数"""
    try:
        data = json.loads(request.body)
        prob = int(data.get('prob', 0))
        conseq = int(data.get('conseq', 1))
        jG_index = int(data.get('jG_index', 0))
        Rp = float(data.get('Rp', 235))
        Rm = float(data.get('Rm', 360))
        KT = float(data.get('KT', 1))
        
        # Safety factors based on probability and consequence
        jm_values = {
            (0, 0): 2, (0, 1): 1.5, (0, 2): 1.5,
            (1, 0): 1.8, (1, 1): 1.35, (1, 2): 1.3
        }
        jp_values = {
            (0, 0): 1.5, (0, 1): 1.5, (0, 2): 1.3,
            (1, 0): 1.35, (1, 1): 1.25, (1, 2): 1.2
        }
        jmt_values = {
            (0, 0): 1.5, (0, 1): 1.5, (0, 2): 1.3,
            (1, 0): 1.35, (1, 1): 1.25, (1, 2): 1.2
        }
        jpt_values = {
            (0, 0): 1, (0, 1): 1, (0, 2): 1,
            (1, 0): 1, (1, 1): 1, (1, 2): 1
        }
        
        jm = jm_values.get((prob, conseq), 1.5)
        jp = jp_values.get((prob, conseq), 1.25)
        jmt = jmt_values.get((prob, conseq), 1.25)
        jpt = jpt_values.get((prob, conseq), 1)
        
        js = 1
        jz = 1
        jW = 1
        j_delta = 0
        jG = [1, 1.25, 1.4][jG_index] if jG_index < 3 else 1
        
        # Total safety factor
        j_ges = max(
            jm / KT * Rp / Rm,
            jp / KT,
            jmt / KT * Rp / Rm,
            jpt / KT
        )
        
        prob_labels = ['High', 'Low']
        conseq_labels = ['High', 'Mean', 'Moderate']
        
        results = [
            {'variable': '', 'description': 'Probability of Stress Occurrence', 'value': prob_labels[prob], 'ref': ''},
            {'variable': '', 'description': 'Consequence of Failure', 'value': conseq_labels[conseq], 'ref': ''},
            {'variable': 'jm', 'description': 'Individual Safety Factor', 'value': jm, 'ref': 'Table 3.5.1'},
            {'variable': 'jp', 'description': 'Individual Safety Factor', 'value': jp, 'ref': 'Table 3.5.1'},
            {'variable': 'j_mt', 'description': 'Individual Safety Factor', 'value': jmt, 'ref': 'Table 3.5.1'},
            {'variable': 'j_pt', 'description': 'Individual Safety Factor', 'value': jpt, 'ref': 'Table 3.5.1'},
            {'variable': 'js', 'description': 'Load Factor', 'value': js, 'ref': 'Load Scaled per STD191010'},
            {'variable': 'jz', 'description': 'Additional Partial Safety Factor', 'value': jz, 'ref': 'Table 3.5.2'},
            {'variable': 'jG', 'description': 'Partial Safety Factor for Cast', 'value': jG, 'ref': '(3.5.2)'},
            {'variable': 'jW', 'description': 'Partial Safety Factor for Welds', 'value': jW, 'ref': '(3.5.3)'},
            {'variable': 'Δj', 'description': 'Partial Safety Term', 'value': j_delta, 'ref': '1 for Ductile Material'},
            {'variable': 'j_ges', 'description': 'Total Safety Factor', 'value': round(j_ges, 3), 'ref': '(3.5.3)'},
        ]
        
        return JsonResponse({'status': 'success', 'results': results, 'j_ges': j_ges})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def calculate_static_step6(request):
    """静强度计算 - 步骤 6: 评估"""
    try:
        data = json.loads(request.body)
        is_weld = data.get('is_weld', False)
        j_ges = float(data.get('j_ges', 1))
        
        if not is_weld:
            sigma_vm = float(data.get('sigma_vm', 200))
            sigma_h = float(data.get('sigma_h', 100))
            h = float(data.get('h', 0.5))
            epsilon_ref = float(data.get('epsilon_ref', 0.2))
            epsilon_0 = float(data.get('epsilon_0', 0.05))
            sigma_SK = float(data.get('sigma_SK', 235))
            
            a_SK = sigma_vm / (sigma_SK / j_ges)
            
            results = [
                {'variable': 'a_SK', 'description': 'DOU of Equivalent Stress', 'value': round(a_SK, 3), 'ref': '(3.6.1)'},
            ]
            
            # Check multiaxiality limits
            if h > 1.333:
                epsilon_Zul = epsilon_0 + 0.3 * ((epsilon_ref - epsilon_0) / 0.3) ** (3 * 1.333)
                n_pl_Zug = min((210000 * epsilon_Zul / (sigma_SK / j_ges)) ** 0.5, 2)
                sigma_SK_Zug = (sigma_SK / j_ges) * n_pl_Zug
                sigma_SH_Zug = 1.333 * sigma_SK_Zug
                a_SH_Zug = sigma_h * j_ges / sigma_SH_Zug
                
                results.extend([
                    {'variable': 'σSK,Zug', 'description': 'Component Strength for Limit Multiaxiality', 'value': round(sigma_SK_Zug, 3), 'ref': '(3.6.6)'},
                    {'variable': 'σSH,Zug', 'description': 'Critical Hydrostatic Stress (tension)', 'value': round(sigma_SH_Zug, 3), 'ref': '(3.6.4)'},
                    {'variable': 'aSH,Zug', 'description': 'DOU of Hydrostatic Stress (tension)', 'value': round(a_SH_Zug, 3), 'ref': '(3.6.3)'},
                ])
            elif h < -1.333:
                n_pl_Druck = min((210000 * epsilon_ref / (sigma_SK / j_ges)) ** 0.5, 2)
                sigma_SK_Druck = (sigma_SK / j_ges) * n_pl_Druck
                sigma_SH_Druck = -1.333 * sigma_SK_Druck
                a_SH_Druck = sigma_h * j_ges / sigma_SH_Druck
                
                results.extend([
                    {'variable': 'σSK,Druck', 'description': 'Component Strength for Limit Multiaxiality', 'value': round(sigma_SK_Druck, 3), 'ref': '(3.6.12)'},
                    {'variable': 'σSH,Druck', 'description': 'Critical Hydrostatic Stress (compression)', 'value': round(sigma_SH_Druck, 3), 'ref': '(3.6.10)'},
                    {'variable': 'aSH,Druck', 'description': 'DOU of Hydrostatic Stress (compression)', 'value': round(a_SH_Druck, 3), 'ref': '(3.6.9)'},
                ])
        else:
            sigma_vm_w = float(data.get('sigma_vm_w', 200))
            sigma_SK_w = float(data.get('sigma_SK_w', 235))
            
            a_SK_w = sigma_vm_w * j_ges / sigma_SK_w
            
            results = [
                {'variable': 'a_SK,w', 'description': 'DOU of Equivalent Stress at Welds', 'value': round(a_SK_w, 3), 'ref': '(3.6.16)'},
            ]
        
        assessment = "PASS" if results[0]['value'] <= 1.0 else "FAIL"
        
        return JsonResponse({'status': 'success', 'results': results, 'assessment': assessment})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@csrf_exempt
def export_static_report(request):
    """导出静强度计算报告为 Excel 文件"""
    try:
        data = json.loads(request.body)
        is_weld = data.get('is_weld', False)
        steps = data.get('steps', [])
        
        step_names = [
            'Step 1: Characteristic Service Stresses',
            'Step 2: Material Properties',
            'Step 3: Design Parameters',
            'Step 4: Component Strength',
            'Step 5: Safety Factors',
            'Step 6: Assessment'
        ]
        
        all_rows = []
        for i, step_data in enumerate(steps):
            step_name = step_data.get('step_name', step_names[i] if i < len(step_names) else f'Step {i+1}')
            variables = step_data.get('variables', [])
            
            all_rows.append(['', '', '', ''])
            all_rows.append([step_name, '', '', ''])
            
            for var in variables:
                all_rows.append([
                    var.get('variable', ''),
                    var.get('description', ''),
                    var.get('value', ''),
                    var.get('ref', '')
                ])
        
        format_list = [0] * 7
        current_row = 0
        for i, step_data in enumerate(steps):
            variables = step_data.get('variables', [])
            format_list[i] = current_row + 1
            current_row += 2 + len(variables)
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sheet1')
        
        format_bgc = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center'})
        format_bgc.set_center_across()
        format1 = workbook.add_format({'num_format': '#,##0.000', 'align': 'center'})
        
        for row_idx, row_data in enumerate(all_rows):
            for col_idx, cell_value in enumerate(row_data):
                worksheet.write(row_idx, col_idx, cell_value)
        
        worksheet.set_column(0, 0, 10, format1)
        worksheet.set_column(1, 1, 45)
        worksheet.set_column(2, 3, 16, format1)
        
        for i, step_name in enumerate(step_names):
            if i < len(steps) and format_list[i] > 0:
                row = format_list[i]
                worksheet.merge_range(row, 0, row, 3, step_name, format_bgc)
        
        workbook.close()
        
        output.seek(0)
        filename = f"static_{'welded' if is_weld else 'non_welded'}_{date.today().strftime('%Y-%m-%d')}.xlsx"
        
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except Exception as e:
        import traceback
        return JsonResponse({'status': 'error', 'message': str(e), 'traceback': traceback.format_exc()})


@csrf_exempt
def calculate_static(request):
    """静强度计算 - 兼容旧接口"""
    try:
        data = json.loads(request.body)
        
        sigma_vm = float(data.get('sigma_vm', 0))
        sigma_x = float(data.get('sigma_x', 0))
        sigma_y = float(data.get('sigma_y', 0))
        sigma_z = float(data.get('sigma_z', 0))
        
        sigma_h = 1/3 * (sigma_x + sigma_y + sigma_z)
        h = sigma_h / sigma_vm if sigma_vm > 0 else 0
        
        results_step1 = [
            {'variable': 'σvm', 'description': 'Max Von-Mises Stress', 'value': sigma_vm, 'ref': 'input'},
            {'variable': 'σx', 'description': 'X Normal Stress', 'value': sigma_x, 'ref': 'input'},
            {'variable': 'σy', 'description': 'Y Normal Stress', 'value': sigma_y, 'ref': 'input'},
            {'variable': 'σz', 'description': 'Z Normal Stress', 'value': sigma_z, 'ref': 'input'},
            {'variable': 'σh', 'description': 'Hydrostatic Stress', 'value': round(sigma_h, 3), 'ref': '(3.1.11)'},
            {'variable': 'h', 'description': 'Degree of Multiaxiality', 'value': round(h, 3), 'ref': '(3.1.10)'},
        ]
        
        return JsonResponse({'status': 'success', 'step1': results_step1})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
