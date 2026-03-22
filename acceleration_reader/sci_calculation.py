"""
Scientific calculation module for acceleration data analysis
Includes filtering, sustained acceleration calculation, and reversal detection
"""

import numpy as np
import pandas as pd
import math
from scipy.signal import butter, lfilter_zi, lfilter

try:
    from numba import njit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    print("Warning: numba not available, using pandas for sustained acceleration calculation")


@njit(parallel=True, cache=True)
def _sustained_acc_numba(data, window_size):
    """
    Numba-optimized sustained acceleration calculation using parallel processing.
    
    For positive sustained: max of rolling minimums (only where min > 0)
    For negative sustained: min of rolling maximums (only where max < 0)
    """
    n = len(data)
    m = n - window_size + 1
    
    # Pre-allocate arrays for results
    min_vals = np.empty(m)
    max_vals = np.empty(m)
    
    # Parallel sliding window computation
    for i in prange(m):
        window = data[i:i + window_size]
        min_vals[i] = np.min(window)
        max_vals[i] = np.max(window)
    
    # For positive sustained: max of rolling mins (only where min > 0)
    pos_mask = min_vals > 0
    if np.any(pos_mask):
        pos_result = np.max(min_vals[pos_mask])
    else:
        pos_result = 0.0
    
    # For negative sustained: min of rolling maxs (only where max < 0)
    neg_mask = max_vals < 0
    if np.any(neg_mask):
        neg_result = np.min(max_vals[neg_mask])
    else:
        neg_result = 0.0
    
    return pos_result, neg_result


def sustained_acc(data, window_size, use_numba=True):
    """
    Calculate sustained acceleration using the fastest available method.
    
    For positive sustained: max of rolling minimums (only where min > 0)
    For negative sustained: min of rolling maximums (only where max < 0)
    
    Parameters:
    -----------
    data : array-like
        Input acceleration data
    window_size : int
        Window size in samples
    use_numba : bool
        Whether to use numba optimization (if available)
    
    Returns:
    --------
    pos_result, neg_result : float
        Positive and negative sustained acceleration values
    """
    data = np.asarray(data)
    if window_size <= 0 or len(data) == 0 or window_size > len(data):
        return 0.0, 0.0
    
    # Use numba if available and requested
    if use_numba and HAS_NUMBA:
        return _sustained_acc_numba(data, window_size)
    
    # Fallback to pandas method
    arr = pd.Series(data)
    
    # For positive sustained: max of rolling mins (only where min > 0)
    rolling_mins = arr.rolling(window_size).min().dropna()
    pos_values = rolling_mins[rolling_mins > 0]
    pos_result = pos_values.max() if len(pos_values) > 0 else 0
    
    # For negative sustained: min of rolling maxs (only where max < 0)
    rolling_maxs = arr.rolling(window_size).max().dropna()
    neg_values = rolling_maxs[rolling_maxs < 0]
    neg_result = neg_values.min() if len(neg_values) > 0 else 0
    
    return pos_result, neg_result


def butter_lowpass(cutoff, fs, order=5):
    """Design a lowpass butterworth filter"""
    nyq = 0.5 * fs
    if nyq <= 0:
        raise ValueError("Sampling frequency must be positive")
    normal_cutoff = min(cutoff / nyq, 0.999999)
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    zi = lfilter_zi(b, a)
    return b, a, zi


def butter_lowpass_filter(data, cutoff, fs, zeropoint=0, order=4):
    """Apply a lowpass butterworth filter to data"""
    if cutoff >= 500 or cutoff <= 0 or fs <= 0:
        return data
    nyq = 0.5 * fs
    if cutoff >= nyq:
        return np.round(np.asarray(data), decimals=4)
    else:
        b, a, zi = butter_lowpass(cutoff, fs, order=order)
        y = np.round(lfilter(b, a, data, zi=zeropoint*zi)[0], decimals=4)
    return y


def process_ASTM(data, dt):
    """
    Process ASTM data using optimized sustained acceleration calculation.
    Uses numba-parallel computation if available for 9x speedup.
    """
    x_array = data.iloc[:, 1].values
    y_array = data.iloc[:, 2].values
    z_array = data.iloc[:, 3].values
    
    # Use optimized sustained_acc function (numba-parallel if available)
    lstx1, xn = sustained_acc(x_array, dt)
    lstx1, xn = round(lstx1, 4), round(xn, 4)
    
    lsty1, yn = sustained_acc(y_array, dt)
    lsty1, yn = round(lsty1, 4), round(yn, 4)
    
    # For z-axis: subtract 1 (baseline) before calculation, add back after
    z_array_adjusted = z_array - 1
    lstz1_raw, zn_raw = sustained_acc(z_array_adjusted, dt)
    lstz1 = round(lstz1_raw + 1, 4)
    zn = round(zn_raw + 1, 4) if zn_raw != 0 else 1
    
    return [lstx1, lsty1, lstz1], [xn, yn, zn]


def process_GB(data, dt):
    """
    Process GB data using optimized sustained acceleration calculation.
    Uses numba-parallel computation if available for 9x speedup.
    """
    y_array = data.iloc[:, 2].values
    z_array = data.iloc[:, 3].values
    
    # Use optimized sustained_acc function (numba-parallel if available)
    yp, yn = sustained_acc(y_array, dt)
    yp, yn = round(yp, 4), round(yn, 4)
    
    # For z-axis: subtract 1 (baseline) before calculation, add back after
    z_array_adjusted = z_array - 1
    zp_raw, zn_raw = sustained_acc(z_array_adjusted, dt)
    zp = round(zp_raw + 1, 4)
    zn = round(zn_raw + 1, 4) if zn_raw != 0 else 1
    
    return [yp, zp], [yn, zn]


def append4(x1, x2, x3, x4):
    """Append four arrays together"""
    x = np.append(x1, x2)
    x = np.append(x, x3)
    x = np.append(x, x4)
    return x


def eggXY(x1, x2, y_max):
    """Generate egg-shaped contour for XY plane"""
    x1 = min(x1, 2)
    y_max = min(y_max, 3)

    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x2
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x1
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x1
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x2
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y_max
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y_max
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y_max
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y_max
    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def eggXZ(x1, x2, y1, y2):
    """Generate egg-shaped contour for XZ plane"""
    x1 = min(x1, 2)
    y1 = min(y1, 2)
    y2 = min(y2, 6)
    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x2
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x1
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x1
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x2
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y2
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y2
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y1
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y1

    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def eggYZ(x, y1, y2):
    """Generate egg-shaped contour for YZ plane"""
    y1 = min(2, y1)
    y2 = min(6, y2)
    x = min(3, x)
    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y2
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y2
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y1
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y1
    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def coef(height, condition):
    """Calculate height coefficient for ASTM limits"""
    if condition == 'x' or condition == 'y':
        if height <= 32:
            return 0.6
        elif height <= 48:
            return height * 0.025 - 0.2
        else:
            return 1

    if condition == 'z':
        if height <= 32:
            return 0.6
        elif height <= 48:
            return height * 0.025 - 0.2
        else:
            return 1


def coordTransform(pitch, seatback, roll, yaw):
    """Transform coordinates based on orientation angles"""
    pitch = pitch / 180 * np.pi
    seatback = seatback / 180 * np.pi
    roll = roll / 180 * np.pi
    yaw = yaw / 180 * np.pi

    P0 = np.array([0, 0, 1])
    R0A = np.array([[math.cos(yaw), -math.sin(yaw), 0], [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
    RAB = np.array([[1, 0, 0], [0, math.cos(roll), math.sin(roll)], [0, math.sin(roll), math.cos(roll)]])
    RBC = np.array(
        [[math.cos(seatback), 0, math.sin(seatback)], [0, 1, 0], [-math.sin(seatback), 0, math.cos(seatback)]])
    RC0 = (np.dot(np.dot(R0A, RAB), RBC)).T

    return np.round(np.dot(RC0, P0), decimals=4)


def detect_z_acceleration_reversal(z_data, time_data, fs):
    """
    Detect excessive Z-acceleration transitions (reversals).
    
    Criteria:
    1. Using a 0.133s sliding window to check if:
       - Minimum acceleration < 0
       - Maximum acceleration > 2
       - Time of minimum occurs BEFORE time of maximum
    
    2. Check 0.2s before the sliding window - all data in this pre-window period
       must be below 0 (negative)
    
    3. If both conditions satisfied, record the reversal event
    
    4. For consecutive overlapping windows that satisfy the criteria, keep only
       the one with the maximum value difference (max - min)
    """
    z_data = np.asarray(z_data)
    time_data = np.asarray(time_data)
    
    # Window sizes in samples
    window_duration = 0.133  # seconds
    pre_window_duration = 0.2  # seconds
    window_size = int(window_duration * fs)
    pre_window_size = int(pre_window_duration * fs)
    
    all_reversals = []
    n = len(z_data)
    
    # Slide through the data with 0.133s window
    for i in range(n - window_size + 1):
        window_start_idx = i
        window_end_idx = i + window_size - 1
        
        window_data = z_data[window_start_idx:window_end_idx + 1]
        window_time = time_data[window_start_idx:window_end_idx + 1]
        
        # Condition 1: Check if min < 0 and max > 2
        min_val = np.min(window_data)
        max_val = np.max(window_data)
        
        if min_val >= 0 or max_val <= 2:
            continue
        
        min_idx_in_window = np.argmin(window_data)
        max_idx_in_window = np.argmax(window_data)
        
        min_time = window_time[min_idx_in_window]
        max_time = window_time[max_idx_in_window]
        
        # Condition 1b: Time of minimum must be before time of maximum
        if min_time >= max_time:
            continue
        
        # Condition 2: Check 0.2s before the window - all data must be below 0
        pre_window_start_idx = max(0, window_start_idx - pre_window_size)
        pre_window_end_idx = window_start_idx - 1
        
        if pre_window_end_idx < pre_window_start_idx:
            continue
        
        pre_window_data = z_data[pre_window_start_idx:pre_window_end_idx + 1]
        
        if np.any(pre_window_data >= 0):
            continue
        
        # Both conditions satisfied - record this reversal
        reversal = {
            'window_start': float(window_time[0]),
            'window_end': float(window_time[-1]),
            'min_time': float(min_time),
            'max_time': float(max_time),
            'min_value': float(min_val),
            'max_value': float(max_val),
            'pre_window_start': float(time_data[pre_window_start_idx]),
            'pre_window_end': float(window_time[0]),
            'window_start_idx': window_start_idx,
            'window_end_idx': window_end_idx,
            'min_idx': window_start_idx + min_idx_in_window,
            'max_idx': window_start_idx + max_idx_in_window,
            'value_diff': float(max_val - min_val)
        }
        all_reversals.append(reversal)
    
    if len(all_reversals) == 0:
        return []
    
    # Deduplicate: keep only the one with max value difference for consecutive windows
    deduplicated = []
    current_group = [all_reversals[0]]
    
    for i in range(1, len(all_reversals)):
        prev = current_group[-1]
        curr = all_reversals[i]
        
        if curr['window_start_idx'] <= prev['window_end_idx']:
            current_group.append(curr)
        else:
            best = max(current_group, key=lambda x: x['value_diff'])
            deduplicated.append(best)
            current_group = [curr]
    
    if len(current_group) > 0:
        best = max(current_group, key=lambda x: x['value_diff'])
        deduplicated.append(best)
    
    return deduplicated


def detect_xy_acceleration_reversal(x_data, y_data, time_data, fs):
    """
    Detect X and Y acceleration reversals (direction changes).
    
    Criteria:
    1. Using a 0.2s sliding window to check if:
       - Minimum acceleration < 0
       - Maximum acceleration > 0
       (This represents a direction change of acceleration)
    
    2. For consecutive windows that satisfy the criteria:
       - Keep only 2 windows per direction: one with minimum negative peak
         and one with maximum positive peak
    """
    x_data = np.asarray(x_data)
    y_data = np.asarray(y_data)
    time_data = np.asarray(time_data)
    
    window_duration = 0.2  # seconds
    window_size = int(window_duration * fs)
    
    def find_reversals_for_axis(axis_data, axis_name):
        all_reversals = []
        n = len(axis_data)
        
        for i in range(n - window_size + 1):
            window_start_idx = i
            window_end_idx = i + window_size - 1
            
            window_data = axis_data[window_start_idx:window_end_idx + 1]
            window_time = time_data[window_start_idx:window_end_idx + 1]
            
            min_val = np.min(window_data)
            max_val = np.max(window_data)
            
            if min_val >= 0 or max_val <= 0:
                continue
            
            min_idx_in_window = np.argmin(window_data)
            max_idx_in_window = np.argmax(window_data)
            
            min_time = window_time[min_idx_in_window]
            max_time = window_time[max_idx_in_window]
            
            reversal = {
                'window_start': float(window_time[0]),
                'window_end': float(window_time[-1]),
                'min_time': float(min_time),
                'max_time': float(max_time),
                'min_value': float(min_val),
                'max_value': float(max_val),
                'axis': axis_name,
                'window_start_idx': window_start_idx,
                'window_end_idx': window_end_idx,
                'min_idx': window_start_idx + min_idx_in_window,
                'max_idx': window_start_idx + max_idx_in_window
            }
            all_reversals.append(reversal)
        
        return all_reversals
    
    def deduplicate_reversals(all_reversals):
        if len(all_reversals) == 0:
            return []
        
        negative_peaks = []
        positive_peaks = []
        
        for r in all_reversals:
            if r['min_value'] < 0:
                negative_peaks.append(r)
            if r['max_value'] > 0:
                positive_peaks.append(r)
        
        result = []
        
        if len(negative_peaks) > 0:
            best_negative = min(negative_peaks, key=lambda x: x['min_value'])
            result.append(best_negative)
        
        if len(positive_peaks) > 0:
            best_positive = max(positive_peaks, key=lambda x: x['max_value'])
            result.append(best_positive)
        
        result.sort(key=lambda x: x['window_start'])
        
        return result
    
    x_reversals = find_reversals_for_axis(x_data, 'x')
    y_reversals = find_reversals_for_axis(y_data, 'y')
    
    x_reversals_dedup = deduplicate_reversals(x_reversals)
    y_reversals_dedup = deduplicate_reversals(y_reversals)

    return {
        'x_reversals': x_reversals_dedup,
        'y_reversals': y_reversals_dedup
    }


def append4(x1, x2, x3, x4):
    """Append four arrays together"""
    x = np.append(x1, x2)
    x = np.append(x, x3)
    x = np.append(x, x4)
    return x


def eggXY(x1, x2, y_max):
    """
    Generate egg-shaped contour for XY plane.

    Parameters:
    -----------
    x1 : float
        X-axis limit 1 (typically negative side)
    x2 : float
        X-axis limit 2 (typically positive side)
    y_max : float
        Y-axis maximum value

    Returns:
    --------
    x_coords, y_coords : ndarray
        Arrays of x and y coordinates for the egg-shaped contour
    """
    x1 = min(x1, 2)
    y_max = min(y_max, 3)

    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x2
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x1
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x1
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x2
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y_max
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y_max
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y_max
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y_max
    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def eggXZ(x1, x2, y1, y2):
    """
    Generate egg-shaped contour for XZ plane.

    Parameters:
    -----------
    x1 : float
        X-axis limit 1 (typically negative side)
    x2 : float
        X-axis limit 2 (typically positive side)
    y1 : float
        Z-axis limit 1 (typically negative side)
    y2 : float
        Z-axis limit 2 (typically positive side)

    Returns:
    --------
    x_coords, z_coords : ndarray
        Arrays of x and z coordinates for the egg-shaped contour
    """
    x1 = min(x1, 2)
    y1 = min(y1, 2)
    y2 = min(y2, 6)
    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x2
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x1
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x1
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x2
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y2
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y2
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y1
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y1

    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def eggYZ(x, y1, y2):
    """
    Generate egg-shaped contour for YZ plane.

    Parameters:
    -----------
    x : float
        Y-axis value
    y1 : float
        Z-axis limit 1 (typically negative side)
    y2 : float
        Z-axis limit 2 (typically positive side)

    Returns:
    --------
    y_coords, z_coords : ndarray
        Arrays of y and z coordinates for the egg-shaped contour
    """
    y1 = min(2, y1)
    y2 = min(6, y2)
    x = min(3, x)
    x11 = np.cos(np.arange(0, math.pi * 0.5, 0.01)) * x
    x22 = np.cos(np.arange(math.pi * 0.5, math.pi, 0.01)) * x
    x33 = np.cos(np.arange(math.pi, math.pi * 1.5, 0.01)) * x
    x44 = np.cos(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * x
    y11 = np.sin(np.arange(0, math.pi * 0.5, 0.01)) * y2
    y22 = np.sin(np.arange(math.pi * 0.5, math.pi, 0.01)) * y2
    y33 = np.sin(np.arange(math.pi, math.pi * 1.5, 0.01)) * y1
    y44 = np.sin(np.arange(math.pi * 1.5, math.pi * 2 + 0.01, 0.01)) * y1
    return append4(x11, x22, x33, x44), append4(y11, y22, y33, y44)


def coef(height, condition):
    """
    Calculate height coefficient for ASTM limits.

    Parameters:
    -----------
    height : float
        Patron height in inches
    condition : str
        Axis condition ('x', 'y', or 'z')

    Returns:
    --------
    coefficient : float
        Height coefficient value
    """
    if condition == 'x' or condition == 'y':
        if height <= 32:
            return 0.6
        elif height <= 48:
            return height * 0.025 - 0.2
        else:
            return 1

    if condition == 'z':
        if height <= 32:
            return 0.6
        elif height <= 48:
            return height * 0.025 - 0.2
        else:
            return 1

    return 1.0
