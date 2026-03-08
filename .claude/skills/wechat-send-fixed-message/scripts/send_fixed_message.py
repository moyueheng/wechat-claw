from __future__ import annotations

import argparse
import random
import time

import AppKit
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)


def key_tap(keycode: int, flags: int = 0) -> None:
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(down, flags)
    CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def paste_text(text: str) -> None:
    pasteboard = AppKit.NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(text, AppKit.NSPasteboardTypeString)
    time.sleep(0.08)
    key_tap(9, kCGEventFlagMaskCommand)  # Cmd+V


def is_stock_analysis_content(text: str) -> bool:
    """判断文本是否包含股票分析或投资建议内容"""
    keywords = [
        '股票', '股价', '股市', '投资', '买入', '卖出', '持有', '评级',
        '目标价', '估值', '市盈率', '市净率', '财报', '业绩', '涨停',
        '跌停', '牛市', '熊市', '多头', '空头', '板块', '行业',
        '证券', '基金', '期货', '期权', '融资融券', '北向资金',
        '主力资金', '游资', '机构', '散户', '利好', '利空',
        '技术分析', '基本面', '消息面', '政策面', '资金面',
        'K线', '均线', '成交量', 'MACD', 'KDJ', 'RSI',
        '支撑位', '压力位', '突破', '回调', '反弹', '反转'
    ]

    text_lower = text.lower()
    for keyword in keywords:
        if keyword in text_lower:
            return True

    return False


def send_fixed_message(target: str, message: str) -> None:
    # 如果是股票分析内容，添加免责声明
    if is_stock_analysis_content(message):
        disclaimer = "\n\n⚠️ 免责声明：以上分析基于公开新闻，结论出自AI，内容仅供参考，不构成投资建议。"
        message = message + disclaimer

    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        "com.tencent.xinWeChat"
    )
    if not apps:
        raise RuntimeError("WeChat is not running")

    apps[0].activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    time.sleep(0.25)

    key_tap(3, kCGEventFlagMaskCommand)  # Cmd+F
    time.sleep(0.2)
    paste_text(target)
    time.sleep(0.3)
    key_tap(36, 0)  # Enter open chat
    time.sleep(0.4)

    paste_text(message)
    time.sleep(0.12)
    key_tap(36, 0)  # Enter send

    # 添加5-10秒随机延迟
    delay = random.uniform(5, 10)
    time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a fixed message to a specific WeChat contact or group."
    )
    parser.add_argument("--target", required=True, help="Contact or group name")
    parser.add_argument("--message", help="Message text to send")
    parser.add_argument("--message-file", help="Path to file containing message text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    # 获取消息内容：优先从文件读取，否则使用 --message
    if args.message_file:
        with open(args.message_file, 'r', encoding='utf-8') as f:
            message = f.read()
    elif args.message:
        message = args.message
    else:
        raise ValueError("Either --message or --message-file must be provided")
    
    send_fixed_message(target=args.target, message=message)
    print("sent_to_target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
