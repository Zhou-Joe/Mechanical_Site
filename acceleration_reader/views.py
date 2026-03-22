"""
Views for the acceleration reader.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .accdata import AccData, RawData
from .analysis import (
    build_astm_payload,
    build_dataset_summary,
    build_gb_payload,
    build_reversal_payload,
    build_trend_payload,
    build_zone_payload,
    get_plot_frame,
    trend_color,
)
from .constants import (
    CONDITION_TYPES,
    DEFAULT_CUTOFF_FREQUENCY,
    MAX_CUTOFF_FREQUENCY,
    RESTRAINT_TYPES,
)
from .session_store import (
    add_dataset,
    clear_datasets,
    find_dataset_record,
    get_session_state,
    load_dataset,
    remove_dataset as remove_dataset_state,
    update_dataset,
)


def home(request):
    context = {
        "default_cutoff": DEFAULT_CUTOFF_FREQUENCY,
        "max_cutoff": MAX_CUTOFF_FREQUENCY,
        "restraint_types": RESTRAINT_TYPES,
        "condition_types": CONDITION_TYPES,
    }
    return render(request, "acceleration_reader/home.html", context)


def _json_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body)


def _normalize_cutoff(value) -> int:
    try:
        cutoff = int(value)
    except (TypeError, ValueError):
        cutoff = DEFAULT_CUTOFF_FREQUENCY
    return max(1, min(cutoff, MAX_CUTOFF_FREQUENCY))


def _normalize_plot_type(value: str | None) -> str:
    if value in {"Raw", "Filter", "Standard"}:
        return value
    return "Standard"


def _resolve_dataset_record(request, payload: dict) -> dict:
    record = find_dataset_record(
        request,
        dataset_id=payload.get("dataset_id"),
        name=payload.get("filename"),
    )
    if not record:
        raise Http404("Dataset not found. Please upload the file again.")
    return record


def _remove_file_if_exists(path: str | Path) -> None:
    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()


def _load_datasets(request, cutoff: int):
    datasets = []
    for record in get_session_state(request)["datasets"]:
        try:
            datasets.append((record, load_dataset(request, record, cutoff)))
        except FileNotFoundError:
            continue
    return datasets


def _build_dashboard_response(request, plot_type: str, cutoff: int, fit_axis: str | None = None) -> dict:
    loaded = _load_datasets(request, cutoff)
    axis_index = {"x": 1, "y": 2, "z": 3}.get((fit_axis or "").lower())
    peak_times = []
    for _, acc_data in loaded:
        frame = get_plot_frame(acc_data, plot_type)
        if axis_index and not frame.empty:
            max_row = int(frame.iloc[:, axis_index].idxmax())
            peak_times.append(float(frame.iloc[max_row, 0]))
        else:
            peak_times.append(0.0)

    base_peak_time = peak_times[0] if axis_index and peak_times else 0.0
    datasets = []
    for index, ((record, acc_data), peak_time) in enumerate(zip(loaded, peak_times)):
        datasets.append(
            build_trend_payload(
                record,
                acc_data,
                plot_type,
                trend_color(index),
                shift_seconds=(peak_time - base_peak_time) if axis_index else 0.0,
            )
        )

    return {
        "success": True,
        "plot_type": plot_type,
        "cutoff": cutoff,
        "fit_axis": fit_axis,
        "datasets": datasets,
    }


def _save_standard_upload(uploaded_file, cutoff: int):
    file_path = default_storage.save(os.path.join("acceleration_uploads", uploaded_file.name), uploaded_file)
    full_path = Path(settings.MEDIA_ROOT) / file_path
    data = AccData(str(full_path), cutoff=cutoff)
    _remove_file_if_exists(full_path)
    return [("standard", data)]


def _save_raw_upload(uploaded_file, cutoff: int):
    file_path = default_storage.save(os.path.join("acceleration_uploads", uploaded_file.name), uploaded_file)
    full_path = Path(settings.MEDIA_ROOT) / file_path
    raw_data = RawData(str(full_path))
    gb_data, astm_data = raw_data.export_data()
    for data in (gb_data, astm_data):
        data.reformat(
            overwrite=True,
            setting_angle=True,
            pitch_angle=0,
            seatback_angle=0,
            roll_angle=0,
            yaw_angle=0,
            cutoff=cutoff,
        )
    _remove_file_if_exists(full_path)
    return [("gb", gb_data), ("astm", astm_data)]


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    try:
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded."}, status=400)

        file_type = request.POST.get("file_type", "standard")
        cutoff = _normalize_cutoff(request.POST.get("cutoff"))
        imported = _save_raw_upload(uploaded_file, cutoff) if file_type == "raw" else _save_standard_upload(uploaded_file, cutoff)

        for dataset_type, data in imported:
            add_dataset(request, data, dataset_type, source_name=uploaded_file.name)

        return JsonResponse(_build_dashboard_response(request, "Standard", cutoff))
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_plot_data(request):
    try:
        payload = _json_body(request)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        fit_axis = payload.get("fit_axis")
        if fit_axis not in {"x", "y", "z", None, ""}:
            fit_axis = None
        return JsonResponse(_build_dashboard_response(request, plot_type, cutoff, fit_axis))
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_astm_fit(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        restraint = payload.get("restraint", "None")
        condition = payload.get("condition", "Normal")
        height = float(payload.get("height", 0) or 0)

        acc_data = load_dataset(request, record, cutoff)
        return JsonResponse(
            {
                "success": True,
                "dataset": build_dataset_summary(record, acc_data, plot_type),
                "astm": build_astm_payload(acc_data, plot_type, restraint, condition, height),
            }
        )
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_gb_fit(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        acc_data = load_dataset(request, record, cutoff)
        return JsonResponse(
            {
                "success": True,
                "dataset": build_dataset_summary(record, acc_data, plot_type),
                "gb": build_gb_payload(acc_data, plot_type),
            }
        )
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_zone_analysis(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        acc_data = load_dataset(request, record, cutoff)
        return JsonResponse(
            {
                "success": True,
                "dataset": build_dataset_summary(record, acc_data, plot_type),
                **build_zone_payload(acc_data, plot_type),
            }
        )
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_reversal_analysis(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        acc_data = load_dataset(request, record, cutoff)
        return JsonResponse(
            {
                "success": True,
                "dataset": build_dataset_summary(record, acc_data, plot_type),
                **build_reversal_payload(acc_data, plot_type),
            }
        )
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def edit_data(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        operation = payload.get("operation")
        values = payload.get("values", {})
        acc_data = load_dataset(request, record, cutoff)

        if operation in {"add", "multiply"}:
            acc_data.edit_data(operation, values, cutoff)
        elif operation == "angle":
            acc_data.reformat(
                overwrite=True,
                setting_angle=True,
                pitch_angle=int(values.get("pitch", 0)),
                seatback_angle=int(values.get("seatback", 0)),
                roll_angle=int(values.get("roll", 0)),
                yaw_angle=int(values.get("yaw", 0)),
                cutoff=cutoff,
            )
        elif operation == "truncate":
            acc_data.truncate_data(int(values.get("start", 0)), int(values.get("end", 0)), cutoff)
        else:
            return JsonResponse({"error": "Unsupported edit operation."}, status=400)

        update_dataset(request, record["id"], acc_data)
        return JsonResponse(_build_dashboard_response(request, plot_type, cutoff, payload.get("fit_axis")))
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_dataset(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        remove_dataset_state(request, record["id"])
        return JsonResponse(_build_dashboard_response(request, plot_type, cutoff, payload.get("fit_axis")))
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def export_dataset(request):
    try:
        payload = _json_body(request)
        record = _resolve_dataset_record(request, payload)
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        export_mode = payload.get("export_mode", "formatted")
        base_filename = (payload.get("base_filename") or Path(record["name"]).stem).strip() or "acceleration_export"
        suffix = payload.get("suffix", ".txt")
        acc_data = load_dataset(request, record, cutoff)

        if export_mode == "formatted":
            acc_data.reformat(overwrite=True, setting_angle=False, cutoff=cutoff)
            buffer = io.StringIO()
            acc_data.rawdata.to_csv(buffer, sep="\t", header=False, index=False)
            filename = f"{base_filename}{suffix}"
        else:
            frame = get_plot_frame(acc_data, plot_type)
            buffer = io.StringIO()
            frame.to_csv(buffer, sep="\t", header=False, index=False)
            filename = f"{base_filename}_{plot_type.lower()}.txt"

        response = HttpResponse(buffer.getvalue(), content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Http404 as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_report(request):
    try:
        from .reporting import build_report_document
    except RuntimeError as exc:
        return JsonResponse({"error": str(exc)}, status=500)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    try:
        payload = _json_body(request)
        dataset_ids = payload.get("dataset_ids") or []
        plot_type = _normalize_plot_type(payload.get("plot_type"))
        cutoff = _normalize_cutoff(payload.get("cutoff"))
        restraint = payload.get("restraint", "None")
        condition = payload.get("condition", "Normal")
        height = float(payload.get("height", 0) or 0)
        astm_view = payload.get("astm_view", "ax")
        gb_view = payload.get("gb_view", "ay")

        selected = []
        for dataset_id in dataset_ids:
            record = find_dataset_record(request, dataset_id=dataset_id)
            if record:
                selected.append((record, load_dataset(request, record, cutoff)))

        if not selected:
            return JsonResponse({"error": "Select at least one dataset for the report."}, status=400)

        report_stream = build_report_document(
            datasets=selected,
            plot_type=plot_type,
            restraint=restraint,
            condition=condition,
            height=height,
            astm_view=astm_view,
            gb_view=gb_view,
        )
        return FileResponse(report_stream, as_attachment=True, filename="acceleration_report.docx")
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_data(request):
    clear_datasets(request)
    return JsonResponse({"success": True, "datasets": []})

