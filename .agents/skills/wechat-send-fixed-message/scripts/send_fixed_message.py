from __future__ import annotations

import argparse
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


def send_fixed_message(target: str, message: str) -> None:
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
