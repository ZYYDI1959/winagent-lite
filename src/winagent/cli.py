import argparse

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

        vks = [hand.key_by_name(part) for part in args.keys.split("+")]
        if len(vks) == 1:
            hand.press(vks[0])
        else:
            hand.hotkey(*vks)
        print(f"KEY {args.keys}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
