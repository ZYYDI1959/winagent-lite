"""bench runner：评测任务执行器。

任务 YAML 放在 bench/tasks/*.yaml，schema:
  id / description / model(可选) / runs(默认5) / verify_level(A|B)
  setup:   [动词列表]   每次运行前重置环境
  steps:   [步骤列表]   与 run_steps 相同的语法
  verify:  {动词: 参数} 成败判定（A=确定性，B=VLM 看图）
  teardown:[动词列表]   每次运行后清理（无论成败）

动词（全部白名单/受控，进程操作为字面量命令函数，杜绝任意命令执行）:
  kill_process: notepad|calc|taskmgr      create_file: {path, content}
  delete_file: <temp 下路径>              press: <键名如 esc>
验证动词:
  file_contains: {path, text}  A级
  process_running: <name> / process_not_running: <name>  A级
  vision_text: <词>  B级（VLM 看图，有噪声，报告中标注）
产出: runs/bench/<id>/run<k>/{trace.json, final.png}
      runs/bench/progress.log  runs/bench/report.md
"""
from __future__ import annotations

import time
from pathlib import Path

from winagent import agent, hand, vision
from winagent.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = REPO_ROOT / "bench" / "tasks"
OUT_ROOT = REPO_ROOT / "runs" / "bench"
TEMP_ROOT = "C:\\Users\\ZY\\AppData\\Local\\Temp"


def _kill_notepad() -> None:
    import subprocess

    subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)


def _kill_calc() -> None:
    import subprocess

    subprocess.run(["taskkill", "/F", "/IM", "CalculatorApp.exe"], capture_output=True)


def _kill_taskmgr() -> None:
    import subprocess

    subprocess.run(["taskkill", "/F", "/IM", "Taskmgr.exe"], capture_output=True)


def _query_notepad() -> str:
    import subprocess

    res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq notepad.exe"], capture_output=True)
    return res.stdout.decode("utf-8", errors="replace")


def _query_calc() -> str:
    import subprocess

    res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CalculatorApp.exe"], capture_output=True)
    return res.stdout.decode("utf-8", errors="replace")


def _query_taskmgr() -> str:
    import subprocess

    res = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Taskmgr.exe"], capture_output=True)
    return res.stdout.decode("utf-8", errors="replace")


def _clear_notepad_session() -> None:
    """删除 Win11 记事本的会话标签记录，防止启动时恢复旧未保存标签页。

    根因：强杀/异常退出后 TabState 残留，下次启动恢复旧标签，
    新输入打进恢复的未保存文档，Ctrl+S 变成另存为对话框。
    """
    tab_state = Path("C:/Users/ZY/AppData/Local/Packages/Microsoft.WindowsNotepad_8wekyb3d8bbwe/LocalState/TabState")
    if tab_state.exists():
        for f in tab_state.iterdir():
            try:
                f.unlink()
            except OSError:
                pass


# 进程操作白名单：名字 -> 字面量命令函数，名字只用于选择
KILLERS = {
    "notepad": _kill_notepad,
    "calc": _kill_calc,
    "taskmgr": _kill_taskmgr,
}
QUERIES = {
    "notepad": _query_notepad,
    "calc": _query_calc,
    "taskmgr": _query_taskmgr,
}
_PROCESS_MARK = {
    "notepad": "notepad.exe",
    "calc": "calculatorapp.exe",
    "taskmgr": "taskmgr.exe",
}


def _safe_temp_path(p: str) -> Path:
    """文件类动词只允许操作 Temp 目录下的路径。"""
    ab = Path(p).resolve()
    if not str(ab).startswith(TEMP_ROOT):
        raise ValueError(f"路径必须在 Temp 目录下: {p}")
    return ab


def _do_verb(verb) -> None:
    if isinstance(verb, str):  # 兼容无参数动词的裸字符串写法
        verb = {verb: True}
    for key, val in verb.items():
        if key == "kill_process":
            fn = KILLERS.get(str(val))
            if fn is None:
                raise ValueError(f"kill_process 白名单外: {val}")
            fn()
        elif key == "clear_notepad_session":
            _clear_notepad_session()
        elif key == "create_file":
            path = _safe_temp_path(val["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(val["content"]), encoding="utf-8")
        elif key == "delete_file":
            p = _safe_temp_path(val)
            if p.exists():
                p.unlink()
        elif key == "press":
            hand.combo(str(val))
        else:
            raise ValueError(f"未知动词: {key}")


def _do_verify(spec: dict, cfg) -> bool:
    for key, val in spec.items():
        if key == "file_contains":
            path = _safe_temp_path(val["path"])
            if not path.exists():
                return False
            if str(val["text"]) not in path.read_text(encoding="utf-8", errors="replace"):
                return False
        elif key == "process_running":
            out = QUERIES[str(val)]().lower()
            if _PROCESS_MARK[str(val)] not in out:
                return False
        elif key == "process_not_running":
            out = QUERIES[str(val)]().lower()
            if _PROCESS_MARK[str(val)] in out:
                return False
        elif key == "vision_text":
            if not vision.ask(str(val), cfg):
                return False
        else:
            raise ValueError(f"未知验证动词: {key}")
    return True


def load_tasks(ids: list[str] | None = None) -> list[dict]:
    import yaml

    tasks = []
    for f in sorted(BENCH_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        if ids is None or data["id"] in ids:
            tasks.append(data)
    return tasks


def run_task_once(task: dict, cfg, out_dir: Path) -> dict:
    """单任务单次运行：setup -> steps -> 截图 -> verify -> teardown。"""
    for verb in task.get("setup", []):
        _do_verb(verb)
    t0 = time.monotonic()
    rec: dict = {"run": None, "steps_ok": False, "verify_ok": None, "ok": False,
                 "duration": 0.0, "reason": ""}
    try:
        res = agent.run_steps(task["steps"], cfg, trace_path=str(out_dir / "trace.json"))
        rec["steps_ok"] = res["success"]
        rec["reason"] = f"failed_step={res['failed_step']}" if not res["success"] else "steps ok"
        img, _ = vision.capture_screen()
        vision.downscale(img, 1600).save(out_dir / "final.png")
        if "verify" in task:
            rec["verify_ok"] = _do_verify(task["verify"], cfg)
            rec["reason"] += f" verify={rec['verify_ok']}"
            rec["ok"] = res["success"] and rec["verify_ok"]
        else:
            rec["ok"] = res["success"]
    except Exception as exc:  # 单次运行崩溃不拖垮整个 bench
        rec["reason"] += f" exception={type(exc).__name__}: {exc}"
    finally:
        rec["duration"] = round(time.monotonic() - t0, 1)
        for verb in task.get("teardown", []):
            try:
                _do_verb(verb)
            except Exception as exc:
                rec["reason"] += f" teardown_err={exc}"
    return rec


def bench(task_ids: list[str] | None = None, runs_override: int | None = None,
          out_root: Path | None = None) -> Path:
    out_root = out_root or OUT_ROOT
    out_root.mkdir(parents=True, exist_ok=True)
    prog = (out_root / "progress.log").open("a", encoding="utf-8")
    results: dict[str, list[dict]] = {}

    for task in load_tasks(task_ids):
        tid = task["id"]
        runs = runs_override or int(task.get("runs", 5))
        cfg = load_config()
        if task.get("model"):
            cfg.vision_model = task["model"]
        results[tid] = []
        prog.write(f"\n===== {tid} model={cfg.vision_model} runs={runs} =====\n")
        prog.flush()
        for k in range(1, runs + 1):
            rd = out_root / tid / f"run{k}"
            rd.mkdir(parents=True, exist_ok=True)
            rec = run_task_once(task, cfg, rd)
            rec["run"] = k
            results[tid].append(rec)
            line = (f"[{time.strftime('%H:%M:%S')}] {tid} run{k}/{runs} "
                    f"{'OK' if rec['ok'] else 'FAIL'} {rec['duration']}s {rec['reason']}")
            print(line, flush=True)
            prog.write(line + "\n")
            prog.flush()

    report = _write_report(results, out_root)
    prog.close()
    return report


def _write_report(results: dict[str, list[dict]], out_root: Path) -> Path:
    tasks = {t["id"]: t for t in load_tasks()}
    lines = [
        "# WinAgent-Lite Benchmark Report",
        "",
        f"- 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 任务数: {len(results)}",
        "",
        "| 任务 | 模型 | 验证级 | 成功/总 | 成功率 | 均耗时(s) | 失败位置 |",
        "|------|------|--------|---------|--------|-----------|----------|",
    ]
    for tid, recs in results.items():
        t = tasks.get(tid, {})
        ok = sum(1 for r in recs if r["ok"])
        dur = [r["duration"] for r in recs]
        fails = {r["reason"].split(" ")[0] for r in recs if not r["ok"]}
        lines.append(
            f"| {tid} | {t.get('model', 'config默认')} | {t.get('verify_level', 'A')} "
            f"| {ok}/{len(recs)} | {ok / len(recs):.0%} | {sum(dur) / len(dur):.1f} "
            f"| {', '.join(sorted(fails)) or '-'} |"
        )
    lines += [
        "",
        "## 说明",
        "- A 级验证 = 文件内容/进程存在等确定性判定；B 级 = VLM 看图判定（存在噪声）。",
        "- 每次运行的完整轨迹与最终截图: runs/bench/<任务>/run<k>/",
        "- 已知交互雷区（任务设计输入）: 另存为类对话框对合成键盘输入免疫；",
        "  视觉小目标定位 7b 不可靠 27b 可用；视觉坐标 1~3% 偏差由容差偏移自愈。",
    ]
    path = out_root / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"report: {path}", flush=True)
    return path
