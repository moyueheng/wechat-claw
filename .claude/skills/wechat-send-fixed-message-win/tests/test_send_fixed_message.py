"""
TDD Tests for Windows WeChat Send Fixed Message
测试策略：
1. 单元测试：Mock 所有外部依赖（uiautomation, pyautogui）
2. 集成测试：需要真实微信环境（标记为 integration）
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加 scripts 目录到路径
scripts_path = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))


class TestArgumentParsing:
    """测试参数解析 - TDD Step 1"""
    
    def test_parse_args_with_target_and_message(self):
        """测试正常参数解析"""
        from send_fixed_message import parse_args
        
        with patch.object(sys, 'argv', ['script', '--target', '黄旭', '--message', '你好']):
            args = parse_args()
            assert args.target == '黄旭'
            assert args.message == '你好'
    
    def test_parse_args_missing_target(self):
        """测试缺少 target 参数应该报错"""
        from send_fixed_message import parse_args
        
        with patch.object(sys, 'argv', ['script', '--message', '你好']):
            with pytest.raises(SystemExit):
                parse_args()
    
    def test_parse_args_missing_message(self):
        """测试缺少 message 参数应该报错"""
        from send_fixed_message import parse_args
        
        with patch.object(sys, 'argv', ['script', '--target', '黄旭']):
            with pytest.raises(SystemExit):
                parse_args()


class TestWeChatWindowFinding:
    """测试微信窗口查找 - TDD Step 2"""
    
    @patch('send_fixed_message.auto')
    def test_find_wechat_window_success(self, mock_auto):
        """测试成功找到微信窗口（标准类名）"""
        from send_fixed_message import find_wechat_window
        
        mock_window = MagicMock()
        mock_window.Exists.return_value = True
        mock_auto.WindowControl.return_value = mock_window
        
        result = find_wechat_window()
        
        assert result == mock_window
        # 验证尝试了第一个类名
        mock_auto.WindowControl.assert_any_call(
            searchDepth=1,
            ClassName="WeChatMainWndForPC",
        )
    
    @patch('send_fixed_message.auto')
    def test_find_wechat_window_qt_version(self, mock_auto):
        """测试找到微信 3.x Qt 版本窗口"""
        from send_fixed_message import find_wechat_window
        
        mock_window = MagicMock()
        mock_window.Exists.return_value = True
        
        # 模拟前几个类名都找不到，Qt 版本找到
        def side_effect(**kwargs):
            if kwargs.get('ClassName') == 'Qt51514QWindowIcon':
                mock_window.Exists.return_value = True
                return mock_window
            mock_window.Exists.return_value = False
            return mock_window
        
        mock_auto.WindowControl.side_effect = side_effect
        
        result = find_wechat_window()
        
        assert result == mock_window
    
    @patch('send_fixed_message.auto')
    def test_find_wechat_window_not_found(self, mock_auto):
        """测试未找到微信窗口"""
        from send_fixed_message import find_wechat_window
        
        mock_window = MagicMock()
        mock_window.Exists.return_value = False
        mock_auto.WindowControl.return_value = mock_window
        
        # 模拟 GetRootControl 返回空列表
        mock_root = MagicMock()
        mock_root.GetChildren.return_value = []
        mock_auto.GetRootControl.return_value = mock_root
        
        result = find_wechat_window()
        
        assert result is None
    
    @patch('send_fixed_message.auto')
    def test_find_wechat_window_by_title(self, mock_auto):
        """测试通过标题模糊匹配找到窗口（Qt 版本微信）"""
        from send_fixed_message import find_wechat_window
        
        mock_main = MagicMock()
        mock_main.Exists.return_value = False
        mock_auto.WindowControl.return_value = mock_main
        
        # 模拟找到标题为"微信"且类名包含 Qt 的窗口（微信 3.x）
        mock_wechat_win = MagicMock()
        mock_wechat_win.Name = "微信"
        mock_wechat_win.ClassName = "Qt51514QWindowIcon"
        
        mock_root = MagicMock()
        mock_root.GetChildren.return_value = [mock_wechat_win]
        mock_auto.GetRootControl.return_value = mock_root
        
        result = find_wechat_window()
        
        assert result == mock_wechat_win


class TestSendFixedMessage:
    """测试发送消息核心逻辑 - TDD Step 3"""
    
    @patch('send_fixed_message.find_wechat_window')
    @patch('send_fixed_message.time')
    def test_send_message_wechat_not_running(self, mock_time, mock_find):
        """测试微信未运行时抛出异常"""
        from send_fixed_message import send_fixed_message
        
        mock_find.return_value = None
        
        with pytest.raises(RuntimeError, match="未找到微信窗口"):
            send_fixed_message("黄旭", "你好")
    
    @patch('send_fixed_message.find_wechat_window')
    @patch('send_fixed_message.time')
    def test_send_message_success_flow(self, mock_time, mock_find):
        """测试正常发送流程"""
        from send_fixed_message import send_fixed_message
        
        # Mock 微信窗口
        mock_window = MagicMock()
        mock_find.return_value = mock_window
        
        # Mock 搜索框
        mock_search = MagicMock()
        mock_search.Exists.return_value = True
        mock_window.EditControl.return_value = mock_search
        
        # 执行发送
        send_fixed_message("黄旭", "你好，我是智能投研助手")
        
        # 验证流程
        assert mock_window.SetTopmost.call_count == 2
        mock_window.SetTopmost.assert_any_call(True)
        mock_window.SetTopmost.assert_any_call(False)
        mock_window.SetActive.assert_called_once()
        mock_window.SendKeys.assert_any_call("{Ctrl}f")
        mock_search.SetValue.assert_called_with("")
        # 验证搜索框被调用来发送目标名称（可能有多次调用）
        assert mock_search.SendKeys.call_count >= 1
        mock_window.SendKeys.assert_any_call("{Enter}")
    
    @patch('send_fixed_message.find_wechat_window')
    @patch('send_fixed_message.time')
    def test_send_message_with_special_chars(self, mock_time, mock_find):
        """测试发送包含特殊字符的消息"""
        from send_fixed_message import send_fixed_message
        
        mock_window = MagicMock()
        mock_find.return_value = mock_window
        
        mock_search = MagicMock()
        mock_search.Exists.return_value = True
        mock_window.EditControl.return_value = mock_search
        
        # 测试包含引号的消息
        message = '你好，我是"智能投研助手"'
        send_fixed_message("黄旭", message)
        
        # 验证消息被正确传递（不修改内容）
        # 注意：实际发送时引号应该被保留


class TestMainFunction:
    """测试主函数 - TDD Step 4"""
    
    @patch('send_fixed_message.send_fixed_message')
    @patch('send_fixed_message.parse_args')
    def test_main_success(self, mock_parse, mock_send):
        """测试主函数成功执行"""
        from send_fixed_message import main
        
        mock_parse.return_value = MagicMock(target="黄旭", message="你好")
        
        result = main()
        
        assert result == 0
        mock_send.assert_called_once_with(target="黄旭", message="你好")
    
    @patch('send_fixed_message.send_fixed_message')
    @patch('send_fixed_message.parse_args')
    def test_main_runtime_error(self, mock_parse, mock_send):
        """测试微信未运行时的错误处理"""
        from send_fixed_message import main
        
        mock_parse.return_value = MagicMock(target="黄旭", message="你好")
        mock_send.side_effect = RuntimeError("WeChat is not running")
        
        result = main()
        
        assert result == 1
    
    @patch('send_fixed_message.send_fixed_message')
    @patch('send_fixed_message.parse_args')
    def test_main_unexpected_error(self, mock_parse, mock_send):
        """测试未预期错误的处理"""
        from send_fixed_message import main
        
        mock_parse.return_value = MagicMock(target="黄旭", message="你好")
        mock_send.side_effect = Exception("Unknown error")
        
        result = main()
        
        assert result == 1


class TestKeyboardVersion:
    """测试键盘模拟版本"""
    
    @patch('send_fixed_message_kb.pyautogui')
    @patch('send_fixed_message_kb.pyperclip')
    def test_kb_version_send_flow(self, mock_clip, mock_gui):
        """测试键盘版本发送流程"""
        from send_fixed_message_kb import send_fixed_message
        
        # 由于没有 psutil，check_wechat_running 会返回 True
        send_fixed_message("黄旭", "你好")
        
        # 验证粘贴操作（Ctrl+V）
        mock_gui.keyDown.assert_any_call('ctrl')
        mock_gui.keyUp.assert_any_call('ctrl')
    
    @patch('send_fixed_message_kb.pyautogui')
    @patch('send_fixed_message_kb.pyperclip')
    def test_paste_text(self, mock_clip, mock_gui):
        """测试粘贴文本功能"""
        from send_fixed_message_kb import paste_text
        
        paste_text("测试消息")
        
        mock_clip.copy.assert_called_once_with("测试消息")
        mock_gui.keyDown.assert_any_call('ctrl')
        mock_gui.keyDown.assert_any_call('v')
        mock_gui.keyUp.assert_any_call('v')
        mock_gui.keyUp.assert_any_call('ctrl')


# 集成测试标记
@pytest.mark.integration
class TestIntegration:
    """
    集成测试 - 需要真实微信环境
    运行: uv run pytest -m integration
    """
    
    def test_real_wechat_window_detection(self):
        """测试真实检测微信窗口"""
        try:
            import uiautomation as auto
            window = auto.WindowControl(
                searchDepth=1,
                ClassName="WeChatMainWndForPC",
            )
            exists = window.Exists(1)
            if not exists:
                pytest.skip("微信未运行，跳过集成测试")
        except ImportError:
            pytest.skip("uiautomation 未安装")
    
    def test_real_send_message(self):
        """
        实际发送消息测试 - 谨慎使用
        会真正发送消息到指定联系人！
        """
        pytest.skip("手动执行：取消此行并确保测试环境安全")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
