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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
