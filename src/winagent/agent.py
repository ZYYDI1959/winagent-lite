"""闭环 agent：定位 -> 点击 -> 验证 -> 容差重试；外加步骤解释器与轨迹记录。

act()        单目标闭环：视觉定位 + 真实点击 + 验证（像素差分 或 出现/消失词）
run_steps()  步骤解释器：launch/wait/type/key/click 序列，返回结构化轨迹
验证优先用像素差分（快且确定），appear/gone 词验证走视觉模型（慢，按需）。
launch 只允许白名单内的已知安全程序，且 subprocess 参数全部为字面量常量。
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from PIL import ImageChops

from winagent import hand, vision
from winagent.config import Config

# 视觉坐标存在 1~3% 相对误差（实测曾差 6px 点到任务栏外），验证失败时按此序列加偏移重试
DEFAULT_OFFSETS = [(0, 0), (0, 10), (0, -10), (10, 0), (-10, 0)]


def _launch_notepad() -> None:
    subprocess.Popen(["notepad.exe"], shell=False)


def _launch_notepad_note() -> None:
    """打开固定的测试笔记文件（场景 fixture；文件需先由 setup 创建）。"""
    subprocess.Popen(
        ["notepad.exe", "C:/Users/ZY/AppData/Local/Temp/winagent_note.txt"],
        shell=False,
    )


def _launch_calc() -> None:
    subprocess.Popen(["calc.exe"], shell=False)


def _launch_explorer() -> None:
    subprocess.Popen(["explorer.exe"], shell=False)


def _launch_taskmgr() -> None:
    subprocess.Popen(["taskmgr.exe"], shell=False)


# 程序白名单：名字 -> 启动函数。数据只用来选函数，进不了命令本身。
LAUNCHERS = {
    "notepad": _launch_notepad,
    "notepad_note": _launch_notepad_note,
    "calc": _launch_calc,
    "explorer": _launch_explorer,
    "taskmgr": _launch_taskmgr,
}


def _launch(name: str) -> None:
    fn = LAUNCHERS.get(str(name).lower())
    if fn is None:
        raise ValueError(f"程序不在白名单: {name!r}，可用: {sorted(LAUNCHERS)}")
    fn()


def _diff_ratio(img_a, img_b, region) -> float:
    a = img_a.crop(tuple(region)).convert("L")
    b = img_b.crop(tuple(region)).convert("L")
    hist = ImageChops.difference(a, b).histogram()
    return sum(hist[21:]) / (a.width * a.height)


def act(
    target: str,
    *,
    cfg: Config | None = None,
    appear: str | None = None,
    gone: str | None = None,
    diff_region: tuple[int, int, int, int] | None = None,
    diff_min: float = 0.05,
    double: bool = False,
    max_tries: int = 5,
    wait_s: float = 1.5,
    offsets: list[tuple[int, int]] | None = None,
) -> dict:
    """定位并点击 target，直到验证通过或重试耗尽。

    验证方式三选一（可组合）：diff_region=点击前后该区域像素变化>=diff_min；
    appear=该词出现在屏幕上；gone=该词从屏幕上消失。都不给则点一次即算完成。
    返回 {ok, attempts, reason}，attempts 逐步记录定位/偏移/点击/验证细节。
    """
    cfg = cfg or Config()
    offsets = offsets or DEFAULT_OFFSETS
    attempts: list[dict] = []

    for i in range(max_tries):
        pos = vision.locate(target, cfg)
        if pos is None:
            attempts.append({"try": i, "locate": "NOT_FOUND"})
            time.sleep(wait_s)
            continue
        ox, oy = offsets[i % len(offsets)]
        x, y = pos[0] + ox, pos[1] + oy
        before = vision.capture_screen()[0] if diff_region else None
        hand.click(x, y, double=double)
        time.sleep(wait_s)

        rec: dict = {"try": i, "locate": list(pos), "offset": [ox, oy], "clicked": [x, y]}

        if diff_region is not None:
            ratio = _diff_ratio(before, vision.capture_screen()[0], diff_region)
            rec["diff"] = round(ratio, 4)
            if ratio >= diff_min:
                attempts.append(rec)
                return {"ok": True, "attempts": attempts, "reason": f"diff {ratio:.3f} >= {diff_min}"}
        if gone is not None and not vision.ask(gone, cfg):
            attempts.append(rec)
            return {"ok": True, "attempts": attempts, "reason": f"'{gone}' 已消失"}
        if appear is not None and vision.ask(appear, cfg):
            attempts.append(rec)
            return {"ok": True, "attempts": attempts, "reason": f"'{appear}' 已出现"}
        if appear is None and gone is None and diff_region is None:
            attempts.append(rec)
            return {"ok": True, "attempts": attempts, "reason": "clicked (未配置验证)"}
        attempts.append(rec)

    return {"ok": False, "attempts": attempts, "reason": f"{max_tries} 次重试耗尽"}


def _focus_guard(step: dict) -> bool:
    """步骤声明了 focus 时，等待前台窗口标题包含该词（默认 10 秒超时）。

    用于消除固定 sleep 的启动竞态：等窗口真的就绪/对话框真的弹出再继续。
    """
    focus = step.get("focus")
    if not focus:
        return True
    return hand.wait_foreground(str(focus), timeout=float(step.get("focus_timeout", 10)))


def _execute_steps(steps: list[dict], cfg: Config | None = None) -> dict:
    """执行步骤序列，返回 {success, done, failed_step, trace}。

    支持的步骤（每个 dict 一个键）:
      launch: "notepad"                  启动白名单程序
      wait: 2.5                          等待秒数
      type: "文本"                       向焦点窗口输入（支持中文）
      key: "ctrl+s"                      单键或组合键
      click: {target, appear, gone, diff_region, double}   闭环点击
    """
    cfg = cfg or Config()
    trace: list[dict] = []

    def record(action: str, **kw) -> None:
        rec = {"step": len(trace), "action": action, "time": time.strftime("%H:%M:%S")}
        rec.update(kw)
        trace.append(rec)
        print(f"  [{rec['step']}] {action} {kw.get('detail', '')}", flush=True)

    for step in steps:
        if "launch" in step:
            _launch(step["launch"])
            fok = _focus_guard(step)
            record("launch", detail=step["launch"], focus_ok=fok)
            if not fok:
                return {"success": False, "done": len(trace), "failed_step": len(trace) - 1, "trace": trace}
        elif "wait" in step:
            time.sleep(float(step["wait"]))
            record("wait", detail=step["wait"])
        elif "type" in step:
            hand.type_text(str(step["type"]))
            record("type", detail=str(step["type"])[:40])
        elif "key" in step:
            hand.combo(str(step["key"]))
            fok = _focus_guard(step)
            record("key", detail=step["key"], focus_ok=fok)
            if not fok:
                return {"success": False, "done": len(trace), "failed_step": len(trace) - 1, "trace": trace}
        elif "click" in step:
            spec = step["click"]
            result = act(
                spec["target"],
                cfg=cfg,
                appear=spec.get("appear"),
                gone=spec.get("gone"),
                diff_region=spec.get("diff_region"),
                double=spec.get("double", False),
                max_tries=spec.get("max_tries", 5),
            )
            record("click", detail=spec["target"], ok=result["ok"], reason=result["reason"], attempts=result["attempts"])
            if not result["ok"]:
                return {"success": False, "done": len(trace), "failed_step": len(trace) - 1, "trace": trace}
        else:
            record("unknown", detail=str(step))
            return {"success": False, "done": len(trace), "failed_step": len(trace) - 1, "trace": trace}

    return {"success": True, "done": len(trace), "failed_step": None, "trace": trace}


def run_steps(steps: list[dict], cfg: Config | None = None, trace_path: str | None = None) -> dict:
    """执行步骤序列并落盘轨迹（成功与失败都会写 trace_path，便于事后诊断）。"""
    result = _execute_steps(steps, cfg)
    if trace_path:
        Path(trace_path).parent.mkdir(exist_ok=True)
        Path(trace_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
