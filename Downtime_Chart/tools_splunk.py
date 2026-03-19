import re
import time
import requests
import csv
import io
from typing import Dict, Any, List
from urllib.parse import urljoin
from src.settings import settings

def _get_auth_headers():
    """
    获取认证头，支持Token和用户名/密码两种方式
    
    Returns:
        tuple: (headers_dict, auth_method_str)
    """
    # 优先使用Token认证
    if settings.SPLUNK_TOKEN:
        return (
            {
                "Authorization": f"Bearer {settings.SPLUNK_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "Bearer Token"
        )
    
    # 其次使用用户名/密码认证
    elif settings.SPLUNK_USERNAME and settings.SPLUNK_PASSWORD:
        from requests.auth import HTTPBasicAuth
        return (
            {
                "Authorization": f"Basic {settings.SPLUNK_USERNAME}:{settings.SPLUNK_PASSWORD}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "Basic Auth"
        )
    
    # 都没有配置
    else:
        raise Exception("未配置Splunk认证信息。请设置SPLUNK_USERNAME/SPLUNK_PASSWORD或SPLUNK_TOKEN")

def lint_spl(spl: str) -> Dict[str, Any]:
    """
    Validate SPL query against security rules.
    
    Args:
        spl: The SPL query to validate
        
    Returns:
        Dict with 'ok' (bool), 'reason' (str if not ok), and 'sanitized_spl' (str)
    """
    if not spl or not spl.strip():
        return {
            "ok": False,
            "reason": "Empty SPL query"
        }
    
    sanitized_spl = " ".join(spl.split())
    
    special_commands = ['artdowntime']
    starts_with_special = any(sanitized_spl.lower().strip().startswith(cmd) for cmd in special_commands)
    
    if not starts_with_special:
        index_pattern = r'index\s*=\s*([^\s\|]+)'
        indexes_found = re.findall(index_pattern, sanitized_spl, re.IGNORECASE)
        
        if not indexes_found:
            return {
                "ok": False,
                "reason": "No index specified. You must specify an index from whitelist.",
                "sanitized_spl": sanitized_spl
            }
        
        for idx in indexes_found:
            if idx not in settings.INDEX_WHITELIST:
                return {
                    "ok": False,
                    "reason": f"Index '{idx}' is not in whitelist. Allowed indexes: {', '.join(settings.INDEX_WHITELIST)}",
                    "sanitized_spl": sanitized_spl
                }
    
    pipe_pattern = r'\|\s*(\w+)'
    first_pipe_match = re.search(pipe_pattern, sanitized_spl)
    
    if first_pipe_match:
        first_command = first_pipe_match.group(1).lower()
        
        if settings.ALLOWED_CMDS:
            if first_command.lower() not in [cmd.lower() for cmd in settings.ALLOWED_CMDS]:
                return {
                    "ok": False,
                    "reason": f"Command '{first_command}' is not in whitelist. Allowed commands: {', '.join(settings.ALLOWED_CMDS)}",
                    "sanitized_spl": sanitized_spl
                }
        elif settings.FORBIDDEN_CMDS:
            for forbidden in settings.FORBIDDEN_CMDS:
                if first_command == forbidden.lower():
                    return {
                        "ok": False,
                        "reason": f"Command '{forbidden}' is forbidden for security reasons.",
                        "sanitized_spl": sanitized_spl
                    }
    
    time_pattern = r'(earliest|latest)\s*=\s*([^\s\|]+)'
    time_matches = re.findall(time_pattern, sanitized_spl, re.IGNORECASE)
    
    if not time_matches:
        return {
            "ok": True,
            "sanitized_spl": sanitized_spl,
            "note": "Query does not include time boundaries. Time range should be provided via function parameters (earliest/latest)."
        }
    
    return {
        "ok": True,
        "sanitized_spl": sanitized_spl
    }

def _create_job(spl: str, earliest: str = "-7d@d", latest: str = "now") -> str:
    """
    Create a Splunk search job.
    
    Args:
        spl: The SPL query
        earliest: Earliest time for the search
        latest: Latest time for the search
        
    Returns:
        Search job ID (sid)
    """
    url = urljoin(settings.SPLUNK_HOST, "/services/search/jobs")
    
    headers, auth_method = _get_auth_headers()
    
    data = {
        "search": spl,
        "output_mode": "json",
        "earliest_time": earliest,
        "latest_time": latest
    }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            verify=settings.SPLUNK_VERIFY_TLS,
            timeout=60
        )
        
        if response.status_code == 201:
            result = response.json()
            sid = result.get("sid")
            if not sid:
                raise Exception("No SID returned from Splunk")
            return sid
        elif response.status_code == 401:
            raise Exception(f"认证失败（{auth_method}）。请检查：1）用户名/密码或Token是否正确 2）是否有访问/search/jobs的权限")
        elif response.status_code == 403:
            raise Exception(f"权限不足（{auth_method}）。请联系管理员确认你有执行搜索的权限")
        else:
            raise Exception(f"创建Job失败（{auth_method}）：{response.status_code} - {response.text[:200]}")
    except requests.exceptions.Timeout:
        raise Exception(f"创建Job超时（{auth_method}）。请检查网络连接")
    except requests.exceptions.ConnectionError as e:
        raise Exception(f"连接失败（{auth_method}）：{str(e)}。请检查Splunk Host地址和网络")
    except Exception as e:
        raise Exception(f"创建Job时发生错误（{auth_method}）：{str(e)}")

def _wait_done(sid: str, timeout: int = 600, poll_interval: int = 2) -> None:
    """
    Wait for a Splunk job to complete.
    
    Args:
        sid: Search job ID
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds
    """
    url = urljoin(settings.SPLUNK_HOST, f"/services/search/jobs/{sid}")
    
    headers, auth_method = _get_auth_headers()
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                url,
                headers=headers,
                params={"output_mode": "json"},
                verify=settings.SPLUNK_VERIFY_TLS,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                entry = result.get("entry", [{}])[0]
                content = entry.get("content", {})
                dispatch_state = content.get("dispatchState")
                
                if dispatch_state == "DONE":
                    return
                elif dispatch_state in ["FAILED", "REJECTED"]:
                    error_msg = content.get("messages", [{}])[0].get("text", "Unknown error")
                    raise Exception(f"Job失败：{dispatch_state} - {error_msg}")
                else:
                    print(f"Job状态：{dispatch_state}...")
                    time.sleep(poll_interval)
            elif response.status_code == 401:
                raise Exception(f"认证失败（{auth_method}）查询Job状态")
            elif response.status_code == 404:
                raise Exception(f"Job不存在：{sid}")
            else:
                raise Exception(f"查询Job状态失败（{auth_method}）：{response.status_code}")
        except requests.exceptions.Timeout:
            raise Exception(f"查询Job状态超时（{auth_method}）")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"连接失败（{auth_method}）：{str(e)}")
        except Exception as e:
            raise Exception(f"查询Job状态时发生错误（{auth_method}）：{str(e)}")
    
    raise Exception(f"Job超时（{timeout}秒）")

def _fetch_results(sid: str, count: int = 50000) -> List[Dict[str, Any]]:
    """
    Fetch results from a completed Splunk job.
    
    Args:
        sid: Search job ID
        count: Maximum number of results to fetch
        
    Returns:
        List of dictionaries with the results
    """
    url = urljoin(settings.SPLUNK_HOST, f"/services/search/jobs/{sid}/results")
    
    headers, auth_method = _get_auth_headers()
    
    params = {
        "output_mode": "json",
        "count": count
    }
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            verify=settings.SPLUNK_VERIFY_TLS,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            rows = result.get("results", [])
            return rows
        elif response.status_code == 401:
            raise Exception(f"认证失败（{auth_method}）获取结果")
        elif response.status_code == 404:
            raise Exception(f"Job不存在：{sid}")
        else:
            raise Exception(f"获取结果失败（{auth_method}）：{response.status_code}")
    except requests.exceptions.Timeout:
        raise Exception(f"获取结果超时（{auth_method}）")
    except requests.exceptions.ConnectionError as e:
        raise Exception(f"连接失败（{auth_method}）：{str(e)}")
    except Exception as e:
        raise Exception(f"获取结果时发生错误（{auth_method}）：{str(e)}")

def run_splunk_job(spl: str, earliest: str = "-7d@d", latest: str = "now", max_rows: int = 1000) -> Dict[str, Any]:
    """
    Execute a Splunk query and return results.
    
    Args:
        spl: The SPL query to execute
        earliest: Earliest time for the search
        latest: Latest time for the search
        max_rows: Maximum number of rows to return in preview
        
    Returns:
        Dict with 'rows' (int), 'columns' (list), 'preview_csv' (str)
    """
    try:
        headers, auth_method = _get_auth_headers()
        print(f"使用认证方式：{auth_method}")
        
        sid = _create_job(spl, earliest, latest)
        print(f"Job创建成功，SID：{sid}")
        
        _wait_done(sid)
        print("Job完成")
        
        rows = _fetch_results(sid, count=50000)
        print(f"获取到{len(rows)}条结果")
        
        total_rows = len(rows)
        
        if total_rows > 0:
            columns = list(rows[0].keys())
        else:
            columns = []
        
        preview_rows = rows[:max_rows]
        
        output = io.StringIO()
        if preview_rows:
            # Collect all unique fieldnames from all rows, not just the first row
            all_fieldnames = set()
            for row in preview_rows:
                all_fieldnames.update(row.keys())
            # Sort fieldnames for consistency, but keep columns order if possible
            fieldnames = list(all_fieldnames)
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(preview_rows)
            preview_csv = output.getvalue()
        else:
            preview_csv = ""
        
        return {
            "rows": total_rows,
            "columns": columns,
            "preview_csv": preview_csv,
            "status": "success"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "rows": 0,
            "columns": [],
            "preview_csv": "",
            "status": "error",
            "error": str(e)
        }
