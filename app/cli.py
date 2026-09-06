import argparse
import asyncio
import json
import webbrowser
from pathlib import Path

from app.dependencies import get_pipeline, get_repository
from app.schemas import SourceConfig, SourceKind


def seed_demo() -> SourceConfig:
    return get_repository().add_source(
        SourceConfig(
            name="离线演示信源",
            url="https://demo.example.com/market-intelligence",
            kind=SourceKind.DEMO,
            tags=["演示", "市场情报"],
        )
    )


async def demo(open_report: bool = False) -> None:
    get_repository().init()
    seed_demo()
    result = await get_pipeline().run()
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    if open_report and result.report_path:
        webbrowser.open(Path(result.report_path).resolve().as_uri())


def main() -> None:
    parser = argparse.ArgumentParser(description="市场情报系统命令行")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="初始化数据库")
    demo_parser = sub.add_parser("demo", help="运行离线端到端演示")
    demo_parser.add_argument("--open", action="store_true", help="完成后打开 HTML 报告")
    run_parser = sub.add_parser("run", help="运行所有已启用信源")
    run_parser.add_argument("--open", action="store_true", help="完成后打开 HTML 报告")
    args = parser.parse_args()

    if args.command == "init-db":
        get_repository().init()
        print("数据库初始化完成")
    elif args.command == "demo":
        asyncio.run(demo(args.open))
    elif args.command == "run":
        result = asyncio.run(get_pipeline().run())
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        if args.open and result.report_path:
            webbrowser.open(Path(result.report_path).resolve().as_uri())


if __name__ == "__main__":
    main()
