"""
Windows 微信消息发送工具 - 键盘模拟版
使用 Windows API 强制激活微信窗口
"""
from __future__ import annotations

import argparse
import sys
import time

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("Error: pyautogui or pyperclip not installed.")
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def force_activate_wechat():
    """使用 Windows API 强制激活微信窗口"""
    try:
        import win32gui
        import win32con
        
        # 查找微信窗口
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if '微信' in title or 'WeChat' in title:
                    extra.append(hwnd)
            return True
        
        handles = []
        win32gui.EnumWindows(callback, handles)
        
        if not handles:
            return None, None
        
        hwnd = handles[0]
        
        # 强制激活窗口
        if win32gui.IsIconic(hwnd):  # 如果最小化
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.3)
        
        # 强制将窗口带到前台
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        
        # 获取窗口位置
        rect = win32gui.GetWindowRect(hwnd)
        return hwnd, (rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1])
        
    except ImportError:
        # 回退到 pygetwindow
        try:
            import pygetwindow as gw
            for title in ['微信', 'WeChat']:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    win = windows[0]
                    if win.isMinimized:
                        win.restore()
                        time.sleep(0.3)
                    win.activate()
                    time.sleep(0.5)
                    return None, (win.left, win.top, win.width, win.height)
        except Exception:
            pass
    except Exception as e:
        print(f"激活窗口失败: {e}")
    
    return None, None


def send_fixed_message(target: str, message: str) -> None:
    """向指定联系人发送消息"""
    # 1. 强制激活微信窗口
    hwnd, win_rect = force_activate_wechat()
    if not win_rect:
        raise RuntimeError("未找到或无法激活微信窗口")
    
    left, top, width, height = win_rect
    
    # 2. 点击窗口中心确保聚焦（有时 SetForegroundWindow 不够）
    center_x = left + width // 2
    center_y = top + height // 2
    pyautogui.click(center_x, center_y)
    time.sleep(0.3)
    
    # 3. 打开搜索 Ctrl+F
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('f')
    pyautogui.keyUp('f')
    pyautogui.keyUp('ctrl')
    time.sleep(0.5)
    
    # 4. 清空并输入目标
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('a')
    pyautogui.keyUp('a')
    pyautogui.keyUp('ctrl')
    time.sleep(0.1)
    
    pyperclip.copy(target)
    time.sleep(0.1)
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('v')
    pyautogui.keyUp('v')
    pyautogui.keyUp('ctrl')
    time.sleep(0.8)
    
    # 5. 按 Enter 选择
    pyautogui.press('enter')
    time.sleep(1.0)
    
    # 6. 重新激活窗口（搜索后可能失焦）
    force_activate_wechat()
    
    # 7. 点击输入框（窗口右下角）
    input_x = left + width - 200
    input_y = top + height - 100
    pyautogui.click(input_x, input_y)
    time.sleep(0.3)
    
    # 8. 输入消息
    pyperclip.copy(message)
    time.sleep(0.1)
    pyautogui.keyDown('ctrl')
    pyautogui.keyDown('v')
    pyautogui.keyUp('v')
    pyautogui.keyUp('ctrl')
    time.sleep(0.3)
    
    # 9. 发送
    pyautogui.press('enter')
    time.sleep(0.3)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a fixed message to a specific WeChat contact"
    )
    parser.add_argument("--target", required=True, help="Contact or group name")
    parser.add_argument("--message", required=True, help="Message text to send")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        send_fixed_message(target=args.target, message=args.message)
        print("sent_to_target")
        return 0
    except RuntimeError as e:
        sys.stderr.buffer.write(f"Error: {e}\n".encode('utf-8'))
        return 1
    except Exception as e:
        sys.stderr.buffer.write(f"Unexpected error: {e}\n".encode('utf-8'))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
