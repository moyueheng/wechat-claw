"""
Windows 微信消息发送工具 - 基于 UI Automation
使用多策略定位输入框，比键盘模拟更稳定可靠
"""
from __future__ import annotations

import argparse
import sys
import time

# 尝试导入 uiautomation，如果失败则提供安装提示
try:
    import uiautomation as auto
except ImportError:
    print("Error: uiautomation not installed.")
    print("Please run: uv pip install uiautomation")
    sys.exit(1)


def find_wechat_window() -> auto.WindowControl | None:
    """查找微信主窗口"""
    # 尝试多种可能的窗口类名（微信 3.x 使用 Qt 框架）
    class_names = [
        "WeChatMainWndForPC",
        "WeChatMainWnd",
        "WeChatWnd",
        "ChatWnd",
        "Qt51514QWindowIcon",  # 微信 3.x Qt 窗口类名
    ]
    
    for class_name in class_names:
        wechat_window = auto.WindowControl(
            searchDepth=1,
            ClassName=class_name,
        )
        if wechat_window.Exists(0.5):
            return wechat_window
    
    # 备用：遍历所有窗口查找包含"微信"标题的窗口
    root = auto.GetRootControl()
    for window in root.GetChildren():
        name = window.Name or ""
        class_name = window.ClassName or ""
        
        # 匹配微信窗口（Qt 框架的微信窗口标题为"微信"）
        if name == "微信" and "Qt" in class_name:
            return window
    
    return None


def find_input_box(wechat: auto.WindowControl) -> auto.EditControl | None:
    """
    查找消息输入框 - 使用多策略定位
    
    策略优先级：
    1. 通过 AutomationId 查找
    2. 通过 Name 查找
    3. 通过位置查找（底部区域的 EditControl）
    4. 通过控件层次结构查找
    """
    # 策略1: 尝试常见的 AutomationId
    automation_ids = ["input_edit", "edit", "InputEdit", "msg_input", "message_input"]
    for aid in automation_ids:
        edit = wechat.EditControl(AutomationId=aid)
        if edit.Exists(0.3):
            return edit
    
    # 策略2: 尝试通过 Name 查找
    names = ["输入", "消息", "", "edit", "input"]
    for name in names:
        edit = wechat.EditControl(Name=name)
        if edit.Exists(0.3):
            return edit
    
    # 策略3: 通过位置和控件类型查找
    # 获取所有 EditControl，找到位于窗口底部偏右的那个（输入框通常在右下角）
    all_edits = wechat.GetChildren()
    candidates = []
    
    def collect_edits(control, depth=0):
        """递归收集所有 EditControl"""
        if depth > 5:  # 限制搜索深度
            return
        
        for child in control.GetChildren():
            if isinstance(child, auto.EditControl):
                # 获取控件位置
                rect = child.BoundingRectangle
                if rect and rect.width > 100 and rect.height > 20:
                    candidates.append((child, rect))
            collect_edits(child, depth + 1)
    
    collect_edits(wechat)
    
    if candidates:
        # 按 Y 坐标排序（从下到上），选择最下方的 EditControl
        # 输入框通常在窗口底部
        wechat_rect = wechat.BoundingRectangle
        if wechat_rect:
            window_bottom = wechat_rect.bottom
            # 选择在窗口底部 200 像素范围内的 EditControl
            bottom_edits = [
                (edit, rect) for edit, rect in candidates 
                if window_bottom - rect.bottom < 200
            ]
            if bottom_edits:
                # 选择最宽的那个（输入框通常较宽）
                bottom_edits.sort(key=lambda x: x[1].width, reverse=True)
                return bottom_edits[0][0]
        
        # 如果没有找到底部的，选择最宽的那个
        candidates.sort(key=lambda x: x[1].width, reverse=True)
        return candidates[0][0]
    
    # 策略4: 尝试找到消息列表区域，然后找它旁边的输入区域
    # 消息列表通常是 ListControl 或 DocumentControl
    msg_list = wechat.ListControl(Name="消息")
    if msg_list.Exists(0.3):
        # 输入框通常在消息列表下方
        list_rect = msg_list.BoundingRectangle
        if list_rect:
            for edit, rect in candidates:
                if rect.top > list_rect.bottom - 50:  # 在消息列表下方
                    return edit
    
    return None


def find_search_box(wechat: auto.WindowControl) -> auto.EditControl | None:
    """查找搜索框"""
    # 尝试常见的 AutomationId
    automation_ids = ["search_text", "search_edit", "SearchEdit", "search"]
    for aid in automation_ids:
        edit = wechat.EditControl(AutomationId=aid)
        if edit.Exists(0.3):
            return edit
    
    # 尝试通过 Name 查找
    names = ["搜索", "search", "Search"]
    for name in names:
        edit = wechat.EditControl(Name=name)
        if edit.Exists(0.3):
            return edit
    
    return None


def send_fixed_message(target: str, message: str) -> None:
    """
    向指定联系人发送消息
    
    流程：
    1. 查找并激活微信窗口
    2. 使用 Ctrl+F 打开搜索
    3. 输入目标联系人名称
    4. 选择并打开聊天
    5. 使用 UI Automation 定位输入框并发送消息
    """
    # 1. 查找微信窗口
    wechat = find_wechat_window()
    if not wechat:
        raise RuntimeError("未找到微信窗口，请确保微信已运行")
    
    # 激活窗口
    wechat.SetTopmost(True)
    wechat.SetActive()
    wechat.SetTopmost(False)
    time.sleep(0.5)
    
    # 2. 打开搜索 (Ctrl+F)
    wechat.SendKeys("{Ctrl}f")
    time.sleep(0.5)
    
    # 3. 查找搜索框并输入目标
    search_box = find_search_box(wechat)
    if search_box:
        search_box.Click()
        time.sleep(0.2)
        search_box.SetValue("")  # 清空
        search_box.SendKeys(target)
        time.sleep(0.6)
    else:
        # 回退：直接发送键盘输入
        wechat.SendKeys(target)
        time.sleep(0.6)
    
    # 4. 按 Enter 选择第一个结果
    wechat.SendKeys("{Enter}")
    time.sleep(0.8)
    
    # 5. 查找消息输入框并使用 UI Automation 发送
    input_box = find_input_box(wechat)
    if input_box:
        # 确保输入框获得焦点
        input_box.Click()
        time.sleep(0.3)
        
        # 清空现有内容
        input_box.SetValue("")
        time.sleep(0.2)
        
        # 输入消息
        input_box.SendKeys(message)
        time.sleep(0.3)
        
        # 6. 发送消息 (Enter)
        # 有些微信版本需要点击发送按钮，有些可以直接按 Enter
        wechat.SendKeys("{Enter}")
        time.sleep(0.3)
    else:
        # 回退：直接发送键盘输入
        wechat.SendKeys(message)
        time.sleep(0.3)
        wechat.SendKeys("{Enter}")
        time.sleep(0.2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="向指定微信联系人或群发送固定消息 (Windows UI Automation 版)"
    )
    parser.add_argument("--target", required=True, help="联系人或群名称")
    parser.add_argument("--message", required=True, help="要发送的消息")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        send_fixed_message(target=args.target, message=args.message)
        print("sent_to_target")
        return 0
    except RuntimeError as e:
        # 使用 utf-8 编码输出，避免 Windows 控制台乱码
        sys.stderr.buffer.write(f"Error: {e}\n".encode('utf-8'))
        return 1
    except Exception as e:
        sys.stderr.buffer.write(f"Unexpected error: {e}\n".encode('utf-8'))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
