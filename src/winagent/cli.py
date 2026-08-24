import argparse
from pathlib import Path

from winagent import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="winagent",
        description="Local vision-driven Windows GUI agent",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="print version")

    p_look = sub.add_parser("look", help="locate a screen element by description")
    p_look.add_argument("target", help="目标描述，越具体越好")
    p_look.add_argument("--model", default=None, help="覆盖 config 里的视觉模型名")
    p_look.add_argument("--config", default=None, help="config.yaml 路径")

    p_click = sub.add_parser("click", help="真实鼠标点击指定坐标")
    p_click.add_argument("x", type=int)
    p_click.add_argument("y", type=int)
    p_click.add_argument("--dbl", action="store_true", help="双击")
    p_click.add_argument("--right", action="store_true", help="右键")

    p_type = sub.add_parser("type", help="向当前焦点窗口输入文本")
    p_type.add_argument("text")
    p_type.add_argument("--delay", type=float, default=0.0, help="输入前等待秒数（先把目标窗口点到前台）")

    p_key = sub.add_parser("key", help="按键或组合键，如 enter / esc / ctrl+s")
    p_key.add_argument("keys", help="用 + 连接，如 ctrl+s、alt+f4")

    p_run = sub.add_parser("run", help="执行 YAML 步骤序列")
    p_run.add_argument("file", help="步骤 YAML 文件路径")
    p_run.add_argument("--config", default=None, help="config.yaml 路径")

    p_bench = sub.add_parser("bench", help="跑评测集")
    p_bench.add_argument("--tasks", default="all", help="任务 id 逗号分隔，或 all")
    p_bench.add_argument("--runs", type=int, default=None, help="覆盖每任务运行次数")

    p_plan = sub.add_parser("plan", help="自然语言目标 -> 步骤序列（本地文本模型规划）")
    p_plan.add_argument("goal")
    p_plan.add_argument("--model", default=None, help="规划模型，默认 qwen3-8b-fast")
    p_plan.add_argument("--execute", action="store_true", help="规划后立即执行（会动键鼠）")

    p_doctor = sub.add_parser("doctor", help="环境自检（被动检查，不动键鼠）")
    p_doctor.add_argument("--config", default=None, help="config.yaml 路径")

    args = parser.parse_args()

    if args.command == "version":
        print(__version__)
    elif args.command == "look":
        from winagent import vision
        from winagent.config import load_config

        cfg = load_config(args.config)
        if args.model:
            cfg.vision_model = args.model
        pos = vision.locate(args.target, cfg)
        if pos is None:
            print("NOT_FOUND")
            raise SystemExit(1)
        print(f"FOUND {pos[0]},{pos[1]}")
    elif args.command == "click":
        from winagent import hand

        hand.click(args.x, args.y, double=args.dbl, right=args.right)
        print(f"CLICKED {args.x},{args.y}")
    elif args.command == "type":
        import time

        from winagent import hand

        if args.delay:
            time.sleep(args.delay)
        hand.type_text(args.text)
        print(f"TYPED {len(args.text)} chars")
    elif args.command == "key":
        from winagent import hand

        hand.combo(args.keys)
        print(f"KEY {args.keys}")
    elif args.command == "run":
        import yaml

        from winagent.agent import run_steps
        from winagent.config import load_config

        data = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))
        import winagent

        repo_root = Path(winagent.__file__).resolve().parents[2]
        trace = repo_root / "runs" / "last_trace.json"
        result = run_steps(data.get("steps", []), load_config(args.config), trace_path=str(trace))
        print(f"RESULT: success={result['success']} steps={result['done']} trace={trace}")
        raise SystemExit(0 if result["success"] else 1)
    elif args.command == "bench":
        from winagent.bench import bench as run_bench

        ids = None if args.tasks == "all" else [t.strip() for t in args.tasks.split(",") if t.strip()]
        report = run_bench(ids, runs_override=args.runs)
        print(f"BENCH-DONE {report}")
    elif args.command == "doctor":
        from winagent import doctor
        from winagent.config import load_config

        raise SystemExit(doctor.main(load_config(args.config)))
    elif args.command == "plan":
        import json as _json

        from winagent import agent, planner
        from winagent.config import load_config

        steps = planner.plan(args.goal, model=args.model, cfg=load_config())
        print(_json.dumps(steps, ensure_ascii=False, indent=2))
        if args.execute:
            result = agent.run_steps(steps, load_config())
            print(f"RESULT: success={result['success']} steps={result['done']}")
            raise SystemExit(0 if result["success"] else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
