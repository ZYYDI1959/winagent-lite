import argparse

from winagent import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="winagent",
        description="Local vision-driven Windows GUI agent",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("version", help="print version")
    args = parser.parse_args()

    if args.command == "version":
        print(__version__)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
