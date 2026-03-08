#!/usr/bin/env python3
"""
扫描新闻目录，识别新增的新闻文件。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_state_file_path() -> Path:
    """获取状态文件路径。"""
    # 从项目根目录开始查找
    current = Path.cwd()
    while current != current.parent:
        state_file = current / "memory" / "news-analysis-state.json"
        if state_file.exists():
            return state_file
        current = current.parent

    # 默认路径
    return Path("memory/news-analysis-state.json")


def get_articles_dir() -> Path:
    """获取新闻文章目录路径。"""
    current = Path.cwd()
    while current != current.parent:
        articles_dir = current / "input" / "data" / "articles"
        if articles_dir.exists():
            return articles_dir
        current = current.parent

    return Path("input/data/articles")


def load_state(state_file: Path) -> dict:
    """加载状态文件。"""
    if not state_file.exists():
        return {
            "lastAnalyzedFile": None,
            "totalAnalyzed": 0,
            "lastAnalysisTime": None
        }

    with open(state_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_all_articles(articles_dir: Path) -> list:
    """
    扫描所有新闻文件，按时间顺序排序。
    返回文件路径列表（按旧到新排序）。
    """
    all_files = []

    if not articles_dir.exists():
        return all_files

    # 遍历日期目录
    date_dirs = sorted(articles_dir.iterdir())
    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue

        # 遍历批次目录
        batch_dirs = sorted(date_dir.iterdir())
        for batch_dir in batch_dirs:
            if not batch_dir.is_dir():
                continue

            # 获取该批次下的所有md文件
            md_files = sorted(batch_dir.glob("*.md"))
            all_files.extend(md_files)

    return all_files


def normalize_path(path_str: str) -> str:
    """标准化路径用于比较。"""
    if not path_str:
        return ""
    return str(Path(path_str).resolve())


def find_new_articles(all_files: list, last_analyzed: Optional[str]) -> list:
    """
    找出新增的新闻文件。

    Args:
        all_files: 所有文件路径列表
        last_analyzed: 上次分析的最后文件路径

    Returns:
        新增文件路径列表
    """
    if not last_analyzed:
        return all_files

    # 标准化上次分析的文件路径
    last_analyzed_normalized = normalize_path(last_analyzed)

    new_files = []
    found_last = False

    for file_path in all_files:
        file_normalized = normalize_path(str(file_path))

        if found_last:
            new_files.append(file_path)
        elif file_normalized == last_analyzed_normalized:
            found_last = True

    # 如果没找到上次分析的文件，返回所有文件
    if not found_last:
        return all_files

    return new_files


def main():
    """主函数。"""
    # 获取路径
    state_file = get_state_file_path()
    articles_dir = get_articles_dir()

    print(f"状态文件: {state_file}", file=sys.stderr)
    print(f"新闻目录: {articles_dir}", file=sys.stderr)

    # 加载状态
    state = load_state(state_file)
    last_analyzed = state.get("lastAnalyzedFile")

    print(f"上次分析文件: {last_analyzed}", file=sys.stderr)
    print(f"已分析总数: {state.get('totalAnalyzed', 0)}", file=sys.stderr)

    # 扫描所有文件
    all_files = scan_all_articles(articles_dir)
    print(f"扫描到文件总数: {len(all_files)}", file=sys.stderr)

    # 找出新增文件
    new_files = find_new_articles(all_files, last_analyzed)
    print(f"新增文件数: {len(new_files)}", file=sys.stderr)

    # 输出结果（JSON格式）
    result = {
        "stateFile": str(state_file),
        "articlesDir": str(articles_dir),
        "lastAnalyzedFile": last_analyzed,
        "totalAnalyzed": state.get("totalAnalyzed", 0),
        "totalFiles": len(all_files),
        "newFilesCount": len(new_files),
        "newFiles": [str(f) for f in new_files]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if len(new_files) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
