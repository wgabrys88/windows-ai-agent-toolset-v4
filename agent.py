from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Tuple

import winapi

TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture screen and return current view with cursor visible.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_mouse",
            "description": "Move mouse using normalized coordinates 0..1000 relative to the screenshot.",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "click_mouse",
            "description": "Left click at current cursor position.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into the focused control.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_down",
            "description": "Scroll down by one notch.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def _post_json(payload: Dict[str, Any], endpoint: str, timeout: int) -> Dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ok_payload(extra: Dict[str, Any] | None = None) -> str:
    d: Dict[str, Any] = {"ok": True}
    if extra:
        d.update(extra)
    return json.dumps(d, ensure_ascii=True, separators=(",", ":"))


def _err_payload(error_type: str, message: str) -> str:
    return json.dumps(
        {"ok": False, "error": {"type": error_type, "message": message}},
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _parse_args(arg_str: Any) -> Tuple[Dict[str, Any] | None, str | None]:
    if arg_str is None:
        arg_str = "{}"
    if not isinstance(arg_str, str):
        return None, _err_payload("invalid_arguments", "arguments must be a JSON string")
    try:
        val = json.loads(arg_str) if arg_str else {}
    except json.JSONDecodeError as e:
        return None, _err_payload("invalid_arguments", f"JSON decode error: {e.msg}")
    if not isinstance(val, dict):
        return None, _err_payload("invalid_arguments", "arguments must decode to an object")
    return val, None


def _parse_xy(arg_str: Any) -> Tuple[float | None, float | None, str | None]:
    args, err = _parse_args(arg_str)
    if err is not None:
        return None, None, err
    if "x" not in args or "y" not in args:
        return None, None, _err_payload("invalid_arguments", "missing x or y")
    try:
        x = float(args["x"])
        y = float(args["y"])
    except (TypeError, ValueError):
        return None, None, _err_payload("invalid_arguments", "x and y must be numbers")
    if x < 0.0:
        x = 0.0
    elif x > 1000.0:
        x = 1000.0
    if y < 0.0:
        y = 0.0
    elif y > 1000.0:
        y = 1000.0
    return x, y, None


def _parse_text(arg_str: Any) -> Tuple[str | None, str | None]:
    args, err = _parse_args(arg_str)
    if err is not None:
        return None, err
    if "text" not in args:
        return "", None
    t = "" if args["text"] is None else str(args["text"])
    t = t.encode("ascii", "ignore").decode("ascii")
    return t, None


# def _prune_old_screenshots(messages: List[Dict[str, Any]], keep_last: int) -> List[Dict[str, Any]]:
#     idxs = [
#         i
#         for i, m in enumerate(messages)
#         if m.get("role") == "user" and isinstance(m.get("content"), list)
#     ]
#     if len(idxs) <= keep_last:
#         return messages
#     drop = set()
#     for i in idxs[:-keep_last]:
#         drop.add(i)
#         if i > 0 and messages[i - 1].get("role") == "tool":
#             drop.add(i - 1)
#     return [m for i, m in enumerate(messages) if i not in drop]

def _prune_old_screenshots(messages: List[Dict[str, Any]], keep_last: int) -> List[Dict[str, Any]]:
    idxs = []
    for i, m in enumerate(messages):
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        if any(isinstance(p, dict) and p.get("type") == "image_url" for p in c):
            idxs.append(i)

    if len(idxs) <= keep_last:
        return messages

    for i in idxs[:-keep_last]:
        file_hint = ""
        if i > 0 and messages[i - 1].get("role") == "tool":
            try:
                meta = json.loads(messages[i - 1].get("content", "{}"))
                if isinstance(meta, dict) and meta.get("ok") and meta.get("file"):
                    file_hint = f" (omitted; file={meta['file']})"
            except Exception:
                pass
        messages[i]["content"] = f"captured image data{file_hint}"

    return messages

# def _prune_old_screenshots(messages: List[Dict[str, Any]], keep_last: int) -> List[Dict[str, Any]]:
#     # Safety: keep at least 1 image if pruning is enabled at all
#     try:
#         keep_last = int(keep_last)
#     except Exception:
#         keep_last = 1
#     keep_last = max(1, keep_last)

#     idxs = []
#     for i, m in enumerate(messages):
#         if m.get("role") != "user":
#             continue
#         c = m.get("content")
#         if not isinstance(c, list):
#             continue
#         if any(isinstance(p, dict) and p.get("type") == "image_url" for p in c):
#             idxs.append(i)

#     if len(idxs) <= keep_last:
#         return messages

#     # Convert older screenshot messages into a compact text stub (keep the file hint if possible)
#     for i in idxs[:-keep_last]:
#         file_hint = ""
#         if i > 0 and messages[i - 1].get("role") == "tool":
#             try:
#                 meta = json.loads(messages[i - 1].get("content", "{}"))
#                 if isinstance(meta, dict) and meta.get("ok") and meta.get("file"):
#                     file_hint = f" (omitted; file={meta['file']})"
#             except Exception:
#                 pass
#         messages[i]["content"] = f"captured image data{file_hint}"

#     return messages


def run_agent(
    system_prompt: str,
    task_prompt: str,
    tools_schema: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> str:
    endpoint = cfg["endpoint"]
    model_id = cfg["model_id"]
    timeout = cfg["timeout"]
    temperature = cfg["temperature"]
    max_tokens = cfg["max_tokens"]
    target_w = cfg["target_w"]
    target_h = cfg["target_h"]
    dump_dir = cfg["dump_dir"]
    dump_prefix = cfg["dump_prefix"]
    dump_start = cfg["dump_start"]
    keep_last_screenshots = cfg["keep_last_screenshots"]
    max_steps = cfg["max_steps"]
    step_delay = cfg["step_delay"]

    os.makedirs(dump_dir, exist_ok=True)

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task_prompt},
    ]

    dump_idx = dump_start
    last_content = ""

    for _ in range(max_steps):
        resp = _post_json(
            {
                "model": model_id,
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": "auto",
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            endpoint,
            timeout,
        )

        msg = resp["choices"][0]["message"]
        messages.append(msg)

        if isinstance(msg.get("content"), str):
            last_content = msg["content"]

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return last_content

        if len(tool_calls) > 1:
            for extra_tc in tool_calls[1:]:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": extra_tc["id"],
                        "name": extra_tc["function"]["name"],
                        "content": _err_payload(
                            "too_many_tool_calls", "only one tool call per response allowed"
                        ),
                    }
                )
            tool_calls = tool_calls[:1]

        tc = tool_calls[0]
        name = tc["function"]["name"]
        arg_str = tc["function"].get("arguments")
        call_id = tc["id"]

        if name == "take_screenshot":
            png_bytes, screen_w, screen_h = winapi.capture_screenshot_png(target_w, target_h)
            fn = os.path.join(dump_dir, f"{dump_prefix}{dump_idx:04d}.png")
            with open(fn, "wb") as f:
                f.write(png_bytes)
            dump_idx += 1

            b64 = base64.b64encode(png_bytes).decode("ascii")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": _ok_payload({"file": fn, "screen_w": screen_w, "screen_h": screen_h}),
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "captured image data"},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
                    ],
                }
            )
            messages = _prune_old_screenshots(messages, keep_last_screenshots)

        elif name == "move_mouse":
            x, y, err = _parse_xy(arg_str)
            if err is not None:
                messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": err})
            else:
                winapi.move_mouse_norm(x, y)
                time.sleep(0.06)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "name": name, "content": _ok_payload()}
                )

        elif name == "click_mouse":
            _, err = _parse_args(arg_str)
            if err is not None:
                messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": err})
            else:
                winapi.click_mouse()
                time.sleep(0.06)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "name": name, "content": _ok_payload()}
                )

        elif name == "type_text":
            text, err = _parse_text(arg_str)
            if err is not None:
                messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": err})
            else:
                winapi.type_text(text or "")
                time.sleep(0.06)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "name": name, "content": _ok_payload()}
                )

        elif name == "scroll_down":
            _, err = _parse_args(arg_str)
            if err is not None:
                messages.append({"role": "tool", "tool_call_id": call_id, "name": name, "content": err})
            else:
                winapi.scroll_down()
                time.sleep(0.06)
                messages.append(
                    {"role": "tool", "tool_call_id": call_id, "name": name, "content": _ok_payload()}
                )

        else:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": _err_payload("unknown_tool", name),
                }
            )

        time.sleep(step_delay)

    return last_content
