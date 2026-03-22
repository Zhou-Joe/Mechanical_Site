from __future__ import annotations

from typing import Any

import numpy as np

from .constants import PLOT_COLORS
from .sci_calculation import (
    coef,
    detect_xy_acceleration_reversal,
    detect_z_acceleration_reversal,
    eggXY,
    eggXZ,
    eggYZ,
    process_ASTM,
    process_GB,
)


def get_plot_frame(acc_data, plot_type: str):
    if plot_type == "Raw":
        return acc_data.data
    if plot_type == "Filter":
        return acc_data.filtered_data
    return acc_data.std_data


def build_dataset_summary(record: dict[str, Any], acc_data, plot_type: str, color: str | None = None) -> dict[str, Any]:
    return {
        "id": record["id"],
        "name": record["name"],
        "dataset_type": record["dataset_type"],
        "color": color,
        "angle_info": acc_data.get_angle_info(),
        "stats": acc_data.get_stats_dict(plot_type),
        "data": acc_data.to_dict(plot_type),
    }


def build_trend_payload(record: dict[str, Any], acc_data, plot_type: str, color: str, shift_seconds: float = 0.0) -> dict[str, Any]:
    data = acc_data.to_dict(plot_type)
    data["time"] = [round(t - shift_seconds, 6) for t in data["time"]]
    return {
        "id": record["id"],
        "name": record["name"],
        "dataset_type": record["dataset_type"],
        "color": color,
        "data": data,
        "stats": acc_data.get_stats_dict(plot_type),
        "angle_info": acc_data.get_angle_info(),
    }


def generate_astm_time_axis() -> list[float]:
    return [
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
        12.5, 12.75, 13, 13.25, 13.5, 13.75, 14,
    ]


def generate_gb_time_axis() -> list[float]:
    x_axis: list[float] = []
    x_axis.extend([round(0.02 + i * 0.0025, 4) for i in range(int((0.1 - 0.02) / 0.0025))])
    x_axis.extend([round(0.1 + i * 0.005, 4) for i in range(int((0.2 - 0.1) / 0.005))])
    x_axis.extend([round(0.2 + i * 0.01, 4) for i in range(int((0.5 - 0.2) / 0.01))])
    x_axis.extend([round(0.5 + i * 0.025, 4) for i in range(int((1 - 0.5) / 0.025))])
    x_axis.extend([round(1 + i * 0.05, 4) for i in range(int((2 - 1) / 0.05))])
    x_axis.extend([round(2 + i * 0.1, 4) for i in range(int((5 - 2) / 0.1))])
    x_axis.extend([round(5 + i * 0.25, 4) for i in range(int((14.25 - 5) / 0.25))])
    return x_axis


def build_astm_payload(acc_data, plot_type: str, restraint: str, condition: str, height: float) -> dict[str, Any]:
    plot_data = get_plot_frame(acc_data, plot_type)
    fs = acc_data.fs
    time_axis = generate_astm_time_axis()
    window_sizes = [max(1, int(t * fs)) for t in time_axis]

    results_p = []
    results_n = []
    for dt in window_sizes:
        dp, dn = process_ASTM(plot_data, dt)
        results_p.append(dp)
        results_n.append(dn)

    ax_p = [r[0] for r in results_p]
    ax_n = [r[0] for r in results_n]
    ay_p = [r[1] for r in results_p]
    ay_n = [r[1] for r in results_n]
    az_p = [r[2] for r in results_p]
    az_n = [r[2] for r in results_n]

    height = float(height or 0)
    base_coef_x = coef(height, "x")
    base_coef_z = coef(height, "z")
    cond_mult = 1.25 if condition in {"E-Stop", "Expected/Permitted Bumping"} else 1.0
    restraint_coef_x = cond_mult * coef(height, "x")
    restraint_coef_z = cond_mult * coef(height, "z")

    base_xy_x, base_xy_y = eggXY(2 * base_coef_x, 6 * base_coef_x, 3 * base_coef_x)
    base_xz_x, base_xz_z = eggXZ(2 * base_coef_z, 6 * base_coef_z, 2 * base_coef_z, 6 * base_coef_z)
    base_yz_y, base_yz_z = eggYZ(3 * base_coef_z, 2 * base_coef_z, 6 * base_coef_z)

    return {
        "time_axis": time_axis,
        "ax_positive": ax_p,
        "ax_negative": ax_n,
        "ay_positive": ay_p,
        "ay_negative": ay_n,
        "ay_left": [abs(v) for v in ay_n],
        "az_positive": az_p,
        "az_negative": az_n,
        "raw_x": plot_data.iloc[:, 1].values.tolist(),
        "raw_y": plot_data.iloc[:, 2].values.tolist(),
        "raw_z": plot_data.iloc[:, 3].values.tolist(),
        "time": plot_data.iloc[:, 0].values.tolist(),
        "base_limits": _get_base_astm_limits(base_coef_x, base_coef_z),
        "base_contours": {
            "xy": {"x": base_xy_x.tolist(), "y": base_xy_y.tolist()},
            "xz": {"x": base_xz_x.tolist(), "z": base_xz_z.tolist()},
            "yz": {"y": base_yz_y.tolist(), "z": base_yz_z.tolist()},
        },
        "restraint": restraint,
        "condition": condition,
        "height": height,
        "restraint_limits": _get_restraint_limits(restraint, restraint_coef_x, restraint_coef_z),
        "restraint_contours": _get_restraint_contours(restraint, restraint_coef_x, restraint_coef_z),
    }


def build_gb_payload(acc_data, plot_type: str) -> dict[str, Any]:
    plot_data = get_plot_frame(acc_data, plot_type)
    fs = acc_data.fs
    time_axis = generate_gb_time_axis()
    results_p = []
    results_n = []

    for dt_seconds in time_axis:
        dt_samples = max(1, int(dt_seconds * fs))
        dp, dn = process_GB(plot_data, dt_samples)
        results_p.append(dp)
        results_n.append(dn)

    return {
        "time_axis": [0.002] + time_axis,
        "ay_positive": [max(0, float(np.max(plot_data.iloc[:, 2].values)))] + [r[0] for r in results_p],
        "ay_negative": [min(0, float(np.min(plot_data.iloc[:, 2].values)))] + [r[0] for r in results_n],
        "az_positive": [max(1, float(np.max(plot_data.iloc[:, 3].values)))] + [r[1] for r in results_p],
        "az_negative": [min(1, float(np.min(plot_data.iloc[:, 3].values)))] + [r[1] for r in results_n],
        "raw_y": plot_data.iloc[:, 2].values.tolist(),
        "raw_z": plot_data.iloc[:, 3].values.tolist(),
        "time": plot_data.iloc[:, 0].values.tolist(),
        "limits": {
            "ay_positive": {"x": [0.01, 0.2, 1, 4], "y": [5, 2, 2, 2]},
            "ay_negative": {"x": [0.01, 0.2, 1, 4], "y": [-5, -2, -2, -2]},
            "az_positive": {"x": [0, 1, 2, 3, 4], "y": [6, 6, 4, 4, 4]},
            "az_negative": {"x": [0, 0.5, 2, 3, 4], "y": [-2, -1.5, -1.5, -1.5, -1.5]},
        },
        "combined_limits": {
            "dt_005": {"x": [-1.8, -1.62, -0.54, 0, 1.8, 5.4, 6], "y_pos": [0, 0.6, 1.8, 2, 1.8, 0.6, 0]},
            "dt_010": {"x": [-1.9, -1.71, -0.57, 0, 1.8, 5.4, 6], "y_pos": [0, 0.741, 2.22, 2.47, 2.22, 0.741, 0]},
            "dt_020": {"x": [-1.95, -1.755, -0.585, 0, 1.8, 5.4, 6], "y_pos": [0, 0.9, 2.7, 3, 2.7, 0.9, 0]},
        },
    }


def build_zone_payload(acc_data, plot_type: str) -> dict[str, Any]:
    plot_data = get_plot_frame(acc_data, plot_type)
    x_data = plot_data.iloc[:, 1].values.tolist()
    z_data = plot_data.iloc[:, 3].values.tolist()
    time_data = plot_data.iloc[:, 0].values.tolist()
    zone_colors = []
    zone_labels = []
    for x_value, z_value in zip(x_data, z_data):
        zone = get_zone(x_value, z_value)
        zone_colors.append(get_zone_color(zone))
        zone_labels.append(zone)

    return {
        "zone_data": {
            "x": x_data,
            "z": z_data,
            "time": time_data,
            "colors": zone_colors,
            "zone_labels": zone_labels,
        },
        "zone_analysis": analyze_acceleration_zones(x_data, z_data, time_data, acc_data.fs),
        "zone_boundaries": get_zone_boundaries(),
    }


def build_reversal_payload(acc_data, plot_type: str) -> dict[str, Any]:
    plot_data = get_plot_frame(acc_data, plot_type)
    x_data = plot_data.iloc[:, 1].values
    y_data = plot_data.iloc[:, 2].values
    z_data = plot_data.iloc[:, 3].values
    time_data = plot_data.iloc[:, 0].values
    fs = acc_data.fs

    z_reversals = detect_z_acceleration_reversal(z_data, time_data, fs)
    xy_reversals = detect_xy_acceleration_reversal(x_data, y_data, time_data, fs)

    return {
        "data": {
            "time": time_data.tolist(),
            "x": x_data.tolist(),
            "y": y_data.tolist(),
            "z": z_data.tolist(),
        },
        "z_reversals": [_convert_z_reversal(reversal) for reversal in z_reversals],
        "xy_reversals": {
            "x_reversals": [_convert_xy_reversal(reversal) for reversal in xy_reversals.get("x_reversals", [])],
            "y_reversals": [_convert_xy_reversal(reversal) for reversal in xy_reversals.get("y_reversals", [])],
        },
    }


def get_zone(x_value: float, z_value: float) -> str:
    line_x_at_y = -3.5 * z_value

    if z_value > 0.7:
        if x_value < -1.2:
            return "Zone 4"
        if x_value < -0.7:
            return "Zone 3"
        if x_value < -0.2:
            return "Zone 2"
        return "Zone 1"

    if z_value > 0.2:
        if x_value < -1.2:
            return "Zone 4"
        if x_value < -0.7:
            return "Zone 3"
        if x_value < 0.2:
            return "Zone 2"
        return "Zone 1"

    if z_value > 0:
        if x_value < line_x_at_y and x_value < -0.2:
            return "Zone 4"
        if x_value < line_x_at_y and -0.2 <= x_value <= 0:
            return "Zone 5"
        return "Zone 3"

    if z_value > -0.2:
        if x_value < line_x_at_y and x_value < 0.7:
            return "Zone 5"
        if x_value >= line_x_at_y and x_value < 0.2:
            return "Zone 5"
        return "Zone 4"

    return "Zone 5"


def analyze_acceleration_zones(x_data, z_data, time_data, fs: int) -> dict[str, Any]:
    if len(time_data) >= 2:
        time_interval = time_data[1] - time_data[0]
    else:
        time_interval = 1.0 / fs if fs else 0.002

    min_duration = 0.2
    min_points = max(1, int(min_duration / time_interval)) if time_interval > 0 else 1
    zone_list = [get_zone(x_value, z_value) for x_value, z_value in zip(x_data, z_data)]
    zone_durations: dict[str, list[dict[str, float]]] = {}

    index = 0
    while index < len(zone_list):
        current_zone = zone_list[index]
        start_idx = index
        while index < len(zone_list) and zone_list[index] == current_zone:
            index += 1
        end_idx = index
        if end_idx - start_idx >= min_points:
            start_time = float(time_data[start_idx])
            end_time = float(time_data[end_idx - 1])
            zone_durations.setdefault(current_zone, []).append(
                {"start_time": start_time, "end_time": end_time, "duration": end_time - start_time}
            )

    severity = {"Zone 5": 5, "Zone 4": 4, "Zone 3": 3, "Zone 2": 2, "Zone 1": 1}
    qualifying = []
    for zone_name, durations in zone_durations.items():
        if zone_name in severity:
            qualifying.append({"zone": zone_name, "severity": severity[zone_name], "durations": durations})
    qualifying.sort(key=lambda item: item["severity"], reverse=True)

    return {"zone_durations": zone_durations, "most_severe": qualifying[0] if qualifying else None}


def get_zone_color(zone: str) -> str:
    zone_colors = {
        "Zone 1": "#ADFF2F",
        "Zone 2": "#FFFF00",
        "Zone 3": "#FFA500",
        "Zone 4": "#FFB6C1",
        "Zone 5": "#FF0000",
    }
    return zone_colors.get(zone, "#3498db")


def get_zone_boundaries() -> dict[str, Any]:
    x_min, x_max = -6.0, 6.0
    y_min, y_max = -4.0, 4.0

    def to_poly(x_values, y_values, color):
        return {"x": np.asarray(x_values).tolist(), "y": np.asarray(y_values).tolist(), "color": color}

    x_line_pts = np.linspace(0, 0.7, 20)
    y_line_pts = -x_line_pts / 3.5
    x_zone5_left = np.concatenate([[x_min, x_min, 0], x_line_pts[1:], [x_min]])
    y_zone5_left = np.concatenate([[-0.2, 0, 0], y_line_pts[1:], [-0.2]])

    y_intersect2 = -0.2 / 3.5
    x_line_mid = np.linspace(0.2, 0, 10)
    y_line_mid = -x_line_mid / 3.5
    x_zone5_bottom_right = np.concatenate([[0, 0.2, 0.2], x_line_mid[1:]])
    y_zone5_bottom_right = np.concatenate([[0, 0, y_intersect2], y_line_mid[1:]])

    x_line_pts2 = np.linspace(0.2, 0.7, 15)
    y_line_pts2 = -x_line_pts2 / 3.5
    x_zone4_bottom = np.concatenate([[0.7, x_max, x_max, 0.2], x_line_pts2])
    y_zone4_bottom = np.concatenate([[-0.2, -0.2, 0, 0], y_line_pts2])

    y_intersect = 0.2 / 3.5
    x_line_left = np.linspace(-0.7, -0.2, 10)
    y_line_left = -x_line_left / 3.5
    x_zone4_upper_left = np.concatenate([[x_min, x_min, -0.7], x_line_left, [-0.2]])
    y_zone4_upper_left = np.concatenate([[0, 0.2, 0.2], y_line_left, [0]])

    x_line_mid_upper = np.linspace(0, -0.2, 10)
    y_line_mid_upper = -x_line_mid_upper / 3.5
    x_zone5_upper = np.concatenate([[-0.2, 0], x_line_mid_upper])
    y_zone5_upper = np.concatenate([[0, 0], y_line_mid_upper])

    x_line_right = np.linspace(-0.7, 0, 20)
    y_line_right = -x_line_right / 3.5
    x_zone3_mid = np.concatenate([x_line_right, [x_max, x_max]])
    y_zone3_mid = np.concatenate([y_line_right, [0, 0.2]])

    boundary_lines = [
        {"x": [-0.7, 0], "y": [0.2, 0], "color": "rgba(0,0,0,0.9)", "dash": "solid", "width": 2},
        {"x": [0, 0.7], "y": [0, -0.2], "color": "rgba(0,0,0,0.9)", "dash": "solid", "width": 2},
        {"x": [-3.5 * y_max, -0.7], "y": [y_max, 0.2], "color": "rgba(0,0,0,0.45)", "dash": "dash", "width": 1},
        {"x": [0.7, -3.5 * y_min], "y": [-0.2, y_min], "color": "rgba(0,0,0,0.45)", "dash": "dash", "width": 1},
        {"x": [-1.2, -1.2], "y": [y_min, y_max], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [-0.7, -0.7], "y": [y_min, y_max], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [-0.2, -0.2], "y": [y_min, y_max], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [0.2, 0.2], "y": [y_min, y_max], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [0.7, 0.7], "y": [y_min, y_max], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [x_min, x_max], "y": [0.7, 0.7], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [x_min, x_max], "y": [0.2, 0.2], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [x_min, x_max], "y": [0, 0], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
        {"x": [x_min, x_max], "y": [-0.2, -0.2], "color": "rgba(0,0,0,0.35)", "dash": "solid", "width": 1},
    ]

    labels = [
        {"x": 3, "y": 3, "text": "Zone 1"},
        {"x": -0.45, "y": 3, "text": "Zone 2"},
        {"x": -0.95, "y": 3, "text": "Zone 3"},
        {"x": -3.5, "y": 3, "text": "Zone 4"},
        {"x": 0, "y": -2, "text": "Zone 5"},
    ]

    return {
        "zone5": [
            to_poly([x_min, x_max, x_max, x_min], [y_min, y_min, -0.2, -0.2], "rgba(255, 0, 0, 0.3)"),
            to_poly(x_zone5_left, y_zone5_left, "rgba(255, 0, 0, 0.3)"),
            to_poly(x_zone5_bottom_right, y_zone5_bottom_right, "rgba(255, 0, 0, 0.3)"),
            to_poly(x_zone5_upper, y_zone5_upper, "rgba(255, 0, 0, 0.3)"),
        ],
        "zone4": [
            to_poly(x_zone4_bottom, y_zone4_bottom, "rgba(255, 182, 193, 0.3)"),
            to_poly(x_zone4_upper_left, y_zone4_upper_left, "rgba(255, 182, 193, 0.3)"),
            to_poly([x_min, -1.2, -1.2, x_min], [0.2, 0.2, 0.7, 0.7], "rgba(255, 182, 193, 0.3)"),
            to_poly([x_min, -1.2, -1.2, x_min], [0.7, 0.7, y_max, y_max], "rgba(255, 182, 193, 0.3)"),
        ],
        "zone3": [
            to_poly(x_zone3_mid, y_zone3_mid, "rgba(255, 165, 0, 0.3)"),
            to_poly([-1.2, -0.7, -0.7, -1.2], [0.2, 0.2, 0.7, 0.7], "rgba(255, 165, 0, 0.3)"),
            to_poly([-1.2, -0.7, -0.7, -1.2], [0.7, 0.7, y_max, y_max], "rgba(255, 165, 0, 0.3)"),
        ],
        "zone2": [
            to_poly([-0.7, 0.2, 0.2, -0.7], [0.2, 0.2, 0.7, 0.7], "rgba(255, 255, 0, 0.3)"),
            to_poly([-0.7, -0.2, -0.2, -0.7], [0.7, 0.7, y_max, y_max], "rgba(255, 255, 0, 0.3)"),
        ],
        "zone1": [
            to_poly([0.2, x_max, x_max, 0.2], [0.2, 0.2, 0.7, 0.7], "rgba(173, 255, 47, 0.3)"),
            to_poly([-0.2, x_max, x_max, -0.2], [0.7, 0.7, y_max, y_max], "rgba(173, 255, 47, 0.3)"),
        ],
        "boundary_lines": boundary_lines,
        "labels": labels,
        "limits": {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max},
    }


def trend_color(index: int) -> str:
    return PLOT_COLORS[index % len(PLOT_COLORS)]


def _get_base_astm_limits(base_coef_x: float, base_coef_z: float) -> dict[str, Any]:
    return {
        "ax_negative": {"x": [0.2, 0.5, 14], "y": [-2, -1.5, -1.5]},
        "ax_positive": {"x": [0.2, 1, 2, 4, 5, 11.8, 12, 14], "y": (np.array([6, 6, 4, 4, 3, 3, 2.5, 2.5]) * base_coef_x).tolist()},
        "ay_positive": {"x": [0.2, 1, 2, 14], "y": (np.array([3, 3, 2, 2]) * base_coef_x).tolist()},
        "az_negative": {"x": [0.2, 0.5, 4, 7, 14], "y": (np.array([-2, -1.5, -1.5, -1.2, -1.2]) * base_coef_x).tolist()},
        "az_positive": {"x": [0.2, 1, 2, 4, 5, 11.8, 12, 14], "y": (np.array([6, 6, 4, 4, 3, 3, 2, 2]) * base_coef_x).tolist()},
    }


def _get_restraint_contours(restraint: str, coef_x: float, coef_z: float) -> dict[str, Any]:
    contours: dict[str, Any] = {}

    if restraint == "Upper Body":
        xa, ya = eggXY(2 * coef_x, 3.6 * coef_x, 3 * coef_x)
        xaa, yaa = eggXY(1.6 * coef_x, 3.6 * coef_x, 2.4 * coef_x)
        xb, yb = eggXZ(2 * coef_z, 3.6 * coef_z, 2 * coef_z, 5 * coef_z)
        xbb, ybb = eggXZ(1.6 * coef_z, 3.6 * coef_z, 1.4 * coef_z, 4.8 * coef_z)
        xc, yc = eggYZ(3 * coef_z, 2 * coef_z, 5 * coef_z)
        xcc, ycc = eggYZ(2.4 * coef_z, 1.4 * coef_z, 4.8 * coef_z)
        contours = {
            "xy": {"x": xa.tolist(), "y": ya.tolist()},
            "xy_dash": {"x": xaa.tolist(), "y": yaa.tolist()},
            "xz": {"x": xb.tolist(), "z": yb.tolist()},
            "xz_dash": {"x": xbb.tolist(), "z": ybb.tolist()},
            "yz": {"y": xc.tolist(), "z": yc.tolist()},
            "yz_dash": {"y": xcc.tolist(), "z": ycc.tolist()},
        }
    elif restraint == "Group Lower Body":
        xa, ya = eggXY(1.7 * coef_x, 2.5 * coef_x, 2.4 * coef_x)
        xaa, yaa = eggXY(1.4 * coef_x, 2.5 * coef_x, 2.1 * coef_x)
        xb, yb = eggXZ(1.7 * coef_z, 2.5 * coef_z, 2 * coef_z, 3.5 * coef_z)
        xbb, ybb = eggXZ(1.4 * coef_z, 2.5 * coef_z, 1 * coef_z, 3 * coef_z)
        xc, yc = eggYZ(2.4 * coef_z, 2 * coef_z, 3.5 * coef_z)
        xcc, ycc = eggYZ(2.1 * coef_z, 1 * coef_z, 3 * coef_z)
        contours = {
            "xy": {"x": xa.tolist(), "y": ya.tolist()},
            "xy_dash": {"x": xaa.tolist(), "y": yaa.tolist()},
            "xz": {"x": xb.tolist(), "z": (yb + 1).tolist()},
            "xz_dash": {"x": xbb.tolist(), "z": (ybb + 1).tolist()},
            "yz": {"y": xc.tolist(), "z": (yc + 1).tolist()},
            "yz_dash": {"y": xcc.tolist(), "z": (ycc + 1).tolist()},
        }
    elif restraint == "Individual Lower Body":
        xa, ya = eggXY(1.8 * coef_x, 2.5 * coef_x, 2.6 * coef_x)
        xaa, yaa = eggXY(1.5 * coef_x, 2.5 * coef_x, 2.2 * coef_x)
        xb, yb = eggXZ(1.8 * coef_z, 2.5 * coef_z, 1.8 * coef_z, 4.8 * coef_z)
        xbb, ybb = eggXZ(1.5 * coef_z, 2.5 * coef_z, 1.2 * coef_z, 4.5 * coef_z)
        xc, yc = eggYZ(2.6 * coef_z, 1.8 * coef_z, 4.8 * coef_z)
        xcc, ycc = eggYZ(2.2 * coef_z, 1.2 * coef_z, 4.5 * coef_z)
        contours = {
            "xy": {"x": xa.tolist(), "y": ya.tolist()},
            "xy_dash": {"x": xaa.tolist(), "y": yaa.tolist()},
            "xz": {"x": xb.tolist(), "z": yb.tolist()},
            "xz_dash": {"x": xbb.tolist(), "z": ybb.tolist()},
            "yz": {"y": xc.tolist(), "z": yc.tolist()},
            "yz_dash": {"y": xcc.tolist(), "z": ycc.tolist()},
        }
    elif restraint in {"No Restraint", "Convenience Restraint"}:
        xa, ya = eggXY(1.5 * coef_x, 2.5 * coef_x, 1.8 * coef_x)
        xaa, yaa = eggXY(1.2 * coef_x, 2.5 * coef_x, 1.2 * coef_x)
        xb, yb = eggXZ(1.5 * coef_z, 2.5 * coef_z, 1.2 * coef_z, 3 * coef_z)
        xbb, ybb = eggXZ(1.2 * coef_z, 2.5 * coef_z, 0.8 * coef_z, 2.8 * coef_z)
        xc, yc = eggYZ(1.8 * coef_z, 1.2 * coef_z, 3 * coef_z)
        xcc, ycc = eggYZ(1.2 * coef_z, 0.8 * coef_z, 2.8 * coef_z)
        contours = {
            "xy": {"x": xa.tolist(), "y": ya.tolist()},
            "xy_dash": {"x": xaa.tolist(), "y": yaa.tolist()},
            "xz": {"x": xb.tolist(), "z": (yb + 1).tolist()},
            "xz_dash": {"x": xbb.tolist(), "z": (ybb + 1).tolist()},
            "yz": {"y": xc.tolist(), "z": (yc + 1).tolist()},
            "yz_dash": {"y": xcc.tolist(), "z": (ycc + 1).tolist()},
        }
    return contours


def _get_restraint_limits(restraint: str, coef_x: float, coef_z: float) -> dict[str, Any]:
    if restraint == "None":
        return {}

    front_astm = np.array([-2, -2, -1.5, -1.5])
    back_astm = np.array([6, 6, 6, 4, 4, 3, 3, 2.5, 2.5])
    lr_astm = np.array([3, 3, 3, 2, 2])
    up_astm = np.array([-2, -2, -1.5, -1.5, -1.2, -1.2])
    down_astm = np.array([6, 6, 6, 4, 4, 3, 3, 2, 2])

    if restraint == "Upper Body":
        a31 = np.maximum(front_astm, np.array([-2, -1.6, -1.2, -1.2]) * coef_x)
        a32 = np.minimum(back_astm, np.array([3.6, 3.6, 3.6, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lr_astm, np.array([3, 2.4, 2.4, 1.6, 1.6]) * coef_x)
        a34 = np.maximum(up_astm, np.array([-2, -1.4, -1, -1, -0.7, -0.7]) * coef_z)
        a35 = np.minimum(down_astm, np.array([5, 4.8, 4.8, 3.4, 3.4, 2.6, 2.6, 1.8, 1.8]) * coef_z)
    elif restraint == "Group Lower Body":
        a31 = np.maximum(front_astm, np.array([-2, -1.6, -1.2, -1.2]) * coef_x)
        a32 = np.minimum(back_astm, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lr_astm, np.array([2.4, 2.1, 2.1, 1.4, 1.4]) * coef_x)
        a34 = np.maximum(up_astm, np.array([-1, 0, 0.2, 0.2, 0.2, 0.2]) * coef_z)
        a35 = np.minimum(down_astm, np.array([4.5, 4, 4, 3.1, 3.1, 2.4, 2.4, 1.7, 1.7]) * coef_z)
    elif restraint == "Individual Lower Body":
        a31 = np.maximum(front_astm, np.array([-1.8, -1.5, -1.1, -1.1]) * coef_x)
        a32 = np.minimum(back_astm, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lr_astm, np.array([2.6, 2.2, 2.2, 1.5, 1.5]) * coef_x)
        a34 = np.maximum(up_astm, np.array([-1.8, -1.2, -0.9, -0.9, -0.6, -0.6]) * coef_z)
        a35 = np.minimum(down_astm, np.array([4.8, 4.5, 4.5, 3.2, 3.2, 2.5, 2.5, 1.8, 1.8]) * coef_z)
    else:
        a31 = np.maximum(front_astm, np.array([-1.5, -1.2, -0.7, -0.7]) * coef_x)
        a32 = np.minimum(back_astm, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coef_x)
        a33 = np.minimum(lr_astm, np.array([1.8, 1.2, 1.2, 0.7, 0.7]) * coef_x)
        a34 = np.maximum(up_astm, np.array([-0.2, 0.2, 0.2, 0.2, 0.2, 0.2]) * coef_z)
        a35 = np.minimum(down_astm, np.array([4, 3.8, 3.8, 2.8, 2.8, 2.2, 2.2, 1.6, 1.6]) * coef_z)

    return {
        "ax_negative": {"x": [0, 0.2, 0.5, 14], "y": a31.tolist()},
        "ax_positive": {"x": [0, 0.2, 1, 2, 4, 5, 11.8, 12, 14], "y": a32.tolist()},
        "ay_positive": {"x": [0, 0.2, 1, 2, 14], "y": a33.tolist()},
        "az_negative": {"x": [0, 0.2, 0.5, 4, 7, 14], "y": a34.tolist()},
        "az_positive": {"x": [0, 0.2, 1, 2, 4, 5, 11.8, 12, 14], "y": a35.tolist()},
    }


def _convert_z_reversal(reversal: dict[str, Any]) -> dict[str, Any]:
    return {
        "window_start": float(reversal.get("window_start", 0)),
        "window_end": float(reversal.get("window_end", 0)),
        "min_time": float(reversal.get("min_time", 0)),
        "max_time": float(reversal.get("max_time", 0)),
        "min_value": float(reversal.get("min_value", 0)),
        "max_value": float(reversal.get("max_value", 0)),
        "pre_window_start": float(reversal.get("pre_window_start", 0)),
        "pre_window_end": float(reversal.get("pre_window_end", 0)),
        "window_start_idx": int(reversal.get("window_start_idx", 0)),
        "window_end_idx": int(reversal.get("window_end_idx", 0)),
        "min_idx": int(reversal.get("min_idx", 0)),
        "max_idx": int(reversal.get("max_idx", 0)),
        "value_diff": float(reversal.get("value_diff", 0)),
    }


def _convert_xy_reversal(reversal: dict[str, Any]) -> dict[str, Any]:
    return {
        "window_start": float(reversal.get("window_start", 0)),
        "window_end": float(reversal.get("window_end", 0)),
        "min_time": float(reversal.get("min_time", 0)),
        "max_time": float(reversal.get("max_time", 0)),
        "min_value": float(reversal.get("min_value", 0)),
        "max_value": float(reversal.get("max_value", 0)),
        "axis": reversal.get("axis", "unknown"),
        "window_start_idx": int(reversal.get("window_start_idx", 0)),
        "window_end_idx": int(reversal.get("window_end_idx", 0)),
        "min_idx": int(reversal.get("min_idx", 0)),
        "max_idx": int(reversal.get("max_idx", 0)),
    }
