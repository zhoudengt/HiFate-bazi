#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
压力测试快捷运行脚本

使用方式：
    # 使用默认配置
    python run_test.py

    # 指定环境
    python run_test.py --env production --host http://your-server:8001

    # 自定义参数
    python run_test.py --users 50 --spawn-rate 10 --run-time 10m
"""

import argparse
import subprocess
import sys
import os

from config import TestConfig


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="HiFate-bazi 后端压力测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 使用默认配置（本地环境）
  python run_test.py

  # 指定生产环境
  python run_test.py --env production --host http://production-server:8001

  # 高并发测试
  python run_test.py --users 50 --spawn-rate 10 --run-time 10m

  # Web UI 模式
  python run_test.py --web-ui

  # 命令行模式（无UI）
  python run_test.py --headless
        """
    )
    
    parser.add_argument(
        "--env",
        choices=["default", "local", "staging", "production", "high_load"],
        default="default",
        help="测试环境配置（默认: default）"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        help="目标服务器地址（覆盖配置文件中的设置）"
    )
    
    parser.add_argument(
        "--users",
        type=int,
        help="并发用户数（覆盖配置文件中的设置）"
    )
    
    parser.add_argument(
        "--spawn-rate",
        type=float,
        help="每秒启动用户数（覆盖配置文件中的设置）"
    )
    
    parser.add_argument(
        "--run-time",
        type=str,
        help="测试持续时间（覆盖配置文件中的设置，如: 5m, 10m, 1h）"
    )
    
    parser.add_argument(
        "--web-ui",
        action="store_true",
        help="使用 Web UI 模式（默认）"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="命令行模式（无UI）"
    )
    
    parser.add_argument(
        "--html-report",
        type=str,
        help="生成 HTML 报告（指定输出文件路径）"
    )
    
    parser.add_argument(
        "--csv-report",
        type=str,
        help="生成 CSV 报告（指定输出目录，不包含文件扩展名）"
    )
    
    return parser.parse_args()


def build_locust_command(args, config):
    """构建 Locust 命令"""
    cmd = ["locust", "-f", "locustfile.py"]
    
    # 设置目标地址
    host = args.host or config["host"]
    cmd.extend(["--host", host])
    
    # Web UI 模式
    if args.web_ui or (not args.headless and not args.users):
        # Web UI 模式：不设置 --headless，用户可以通过浏览器控制
        if args.users:
            cmd.extend(["--users", str(args.users)])
        if args.spawn_rate:
            cmd.extend(["--spawn-rate", str(args.spawn_rate)])
        if args.run_time:
            cmd.extend(["--run-time", args.run_time])
        return cmd
    
    # 命令行模式（headless）
    if args.headless or args.users:
        cmd.append("--headless")
        
        users = args.users or config["users"]
        spawn_rate = args.spawn_rate or config["spawn_rate"]
        run_time = args.run_time or config["run_time"]
        
        cmd.extend(["--users", str(users)])
        cmd.extend(["--spawn-rate", str(spawn_rate)])
        cmd.extend(["--run-time", run_time])
        
        # 报告选项
        if args.html_report:
            cmd.extend(["--html", args.html_report])
        
        if args.csv_report:
            cmd.extend(["--csv", args.csv_report])
        
        return cmd
    
    # 默认：Web UI 模式
    return cmd


def main():
    """主函数"""
    args = parse_args()
    
    # 加载配置
    config = TestConfig.get_config(args.env)
    
    # 打印配置信息
    print("\n" + "=" * 60)
    print("压力测试配置")
    print("=" * 60)
    TestConfig.print_config(config)
    print()
    
    # 构建命令
    cmd = build_locust_command(args, config)
    
    # 打印执行的命令
    print("执行命令:")
    print("  " + " ".join(cmd))
    print()
    
    # 切换到 stress_test 目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 执行 Locust
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n错误: Locust 执行失败 (退出码: {e.returncode})")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
