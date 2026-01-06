from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import winapi
from agent import TOOLS_SCHEMA, run_agent

LOG_MONTH_DIR = "2026-01"


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Invalid scenarios.json")
    return data


def _get_env_str(name: str, default: str) -> str:
    v = os.environ.get(name, "").strip()
    return v if v else default


def _get_env_int(name: str, default: int) -> int:
    v = os.environ.get(name, "").strip()
    return default if not v else int(v)


def _get_env_float(name: str, default: float) -> float:
    v = os.environ.get(name, "").strip()
    return default if not v else float(v)


def _extract_json_from_position(lines: List[str], start_idx: int) -> Tuple[Optional[dict], int]:
    json_lines: List[str] = []
    brace_count = 0
    in_string = False
    escape_next = False
    i = start_idx

    while i < len(lines):
        line = lines[i]
        for ch in line:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
            if not in_string:
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
        json_lines.append(line)
        if brace_count == 0 and json_lines:
            break
        i += 1

    try:
        obj = json.loads("\n".join(json_lines))
        return obj, i + 1
    except json.JSONDecodeError:
        return None, i + 1


def _summarize_data_image_url(url: str) -> str:
    if not isinstance(url, str) or not url.startswith("data:image/"):
        return url
    comma = url.find(",")
    if comma == -1:
        return url
    header = url[: comma + 1]
    payload = url[comma + 1 :]
    if len(payload) < 100:
        return url
    sha = hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"{header}[b64 sha={sha} len={len(payload)}]"


def _truncate_base64_images(obj: Any) -> Any:
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "url" and isinstance(v, str):
                obj[k] = _summarize_data_image_url(v)
            else:
                _truncate_base64_images(v)
    elif isinstance(obj, list):
        for it in obj:
            _truncate_base64_images(it)
    return obj


def _clean_log_file(input_path: Path) -> Path:
    content = input_path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    cleaned: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if re.search(r"Received request: POST to /v1/chat/completions with body (\{.*)$", line):
            ts = re.match(r"\[([^\]]+)\]", line)
            timestamp = ts.group(1) if ts else "TIMESTAMP"

            cleaned.append(f"\n{'='*80}")
            cleaned.append(f"[{timestamp}] REQUEST TO MODEL:")
            cleaned.append("=" * 80)

            brace_pos = line.find("{")
            first_line = line[brace_pos:] if brace_pos != -1 else ""
            temp_lines = [first_line] + lines[i + 1 :]
            obj, offset = _extract_json_from_position(temp_lines, 0)
            if obj is not None:
                _truncate_base64_images(obj)
                cleaned.append(json.dumps(obj, indent=2))
                i += offset
            else:
                cleaned.append("[ERROR: Could not parse JSON]")
                i += 1
            continue

        if re.search(r"Generated prediction: (\{.*)$", line):
            ts = re.match(r"\[([^\]]+)\]", line)
            timestamp = ts.group(1) if ts else "TIMESTAMP"

            cleaned.append(f"\n{'='*80}")
            cleaned.append(f"[{timestamp}] RESPONSE FROM MODEL:")
            cleaned.append("=" * 80)

            brace_pos = line.find("{")
            first_line = line[brace_pos:] if brace_pos != -1 else ""
            temp_lines = [first_line] + lines[i + 1 :]
            obj, offset = _extract_json_from_position(temp_lines, 0)
            if obj is not None:
                _truncate_base64_images(obj)
                cleaned.append(json.dumps(obj, indent=2))
                i += offset
            else:
                cleaned.append("[ERROR: Could not parse JSON]")
                i += 1
            continue

        i += 1

    out_path = input_path.with_name(input_path.stem + "_clean" + input_path.suffix)
    out_path.write_text("\n".join(cleaned), encoding="utf-8")
    return out_path


def _parse_log_ts(line: str) -> Optional[datetime]:
    m = re.match(r"^\[([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})\]", line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _export_and_clean_current_run(logs_dir: Path, start_dt: datetime, end_dt: datetime) -> Tuple[Path, Path]:
    time.sleep(5)

    log_files = [p for p in logs_dir.iterdir() if p.is_file()]
    if not log_files:
        raise FileNotFoundError(f"No log files found in: {logs_dir}")

    src = max(log_files, key=lambda p: p.stat().st_mtime)
    content = src.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    t0 = start_dt - timedelta(seconds=2)
    t1 = end_dt + timedelta(seconds=2)

    picked: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        is_req = "Received request: POST to /v1/chat/completions with body" in line
        is_resp = "Generated prediction:" in line
        if not (is_req or is_resp):
            i += 1
            continue

        ts = _parse_log_ts(line)

        brace_pos = line.find("{")
        offset = 1
        if brace_pos != -1:
            first_line = line[brace_pos:]
            temp_lines = [first_line] + lines[i + 1 :]
            _, offset = _extract_json_from_position(temp_lines, 0)
            if offset < 1:
                offset = 1

        if ts is not None and t0 <= ts <= t1:
            picked.extend(lines[i : i + offset])

        i += offset

    cmd = "python " + " ".join(sys.argv)
    safe_cmd = re.sub(r"[^A-Za-z0-9._-]+", "_", cmd).strip("_")

    out_dir = Path(__file__).resolve().parent
    ext = src.suffix if src.suffix else ".log"
    raw_path = out_dir / f"{safe_cmd}_lmstudio_raw{ext}"
    raw_path.write_text("\n".join(picked), encoding="utf-8")

    clean_path = _clean_log_file(raw_path)
    return raw_path, clean_path


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Usage: python main.py scenarios.json <scenario_num>")

    scenarios_path = sys.argv[1]
    scenario_num = int(sys.argv[2])

    winapi.init_dpi()

    data = _load_json(scenarios_path)
    system_prompt = str(data.get("system_prompt", ""))

    scenarios = data.get("scenarios", [])
    if not isinstance(scenarios, list) or scenario_num < 1 or scenario_num > len(scenarios):
        sys.exit("Invalid scenario")

    sc = scenarios[scenario_num - 1]
    if not isinstance(sc, dict):
        sys.exit("Invalid scenario")

    task_prompt = str(sc.get("task_prompt", "")).strip()
    if not task_prompt:
        sys.exit("Invalid scenario")

    cfg = {
        "endpoint": _get_env_str("LMSTUDIO_ENDPOINT", "http://localhost:1234/v1/chat/completions"),
        "model_id": _get_env_str("LMSTUDIO_MODEL", "model-identifier"),
        "timeout": _get_env_int("LMSTUDIO_TIMEOUT", 240),
        "temperature": _get_env_float("LMSTUDIO_TEMPERATURE", 0.2),
        "max_tokens": _get_env_int("LMSTUDIO_MAX_TOKENS", 2048),
        "target_w": _get_env_int("AGENT_IMAGE_W", 1344),
        "target_h": _get_env_int("AGENT_IMAGE_H", 756),
        "dump_dir": _get_env_str("AGENT_DUMP_DIR", "dumps"),
        "dump_prefix": _get_env_str("AGENT_DUMP_PREFIX", "screen_"),
        "dump_start": _get_env_int("AGENT_DUMP_START", 1),
        "keep_last_screenshots": _get_env_int("AGENT_KEEP_LAST_SCREENSHOTS", 2),
        "max_steps": _get_env_int("AGENT_MAX_STEPS", 10),
        "step_delay": _get_env_float("AGENT_STEP_DELAY", 0.4),
    }

    user_home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    logs_dir = user_home / ".lmstudio" / "server-logs" / LOG_MONTH_DIR

    start_dt = datetime.now()
    out = run_agent(system_prompt, task_prompt, TOOLS_SCHEMA, cfg)
    end_dt = datetime.now()

    if out:
        print(out)

    raw_path, clean_path = _export_and_clean_current_run(logs_dir, start_dt, end_dt)
    print(f"LM Studio raw log written to: {raw_path}")
    print(f"LM Studio cleaned log written to: {clean_path}")


if __name__ == "__main__":
    main()
