#!/usr/bin/env python3
"""
扫描新闻目录，识别待分析的新闻文件。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_articles_dir() -> Path:
    """获取新闻文章目录路径。"""
    current = Path.cwd()
    while current != current.parent:
        articles_dir = current / "input" / "data" / "articles"
        if articles_dir.exists():
            return articles_dir
        current = current.parent

    return Path("input/data/articles")


def get_archive_dir(articles_dir: Path) -> Path:
    """获取归档目录路径。"""
    return articles_dir / "archived"


def scan_all_articles(articles_dir: Path) -> list:
    """
    扫描所有未归档的新闻文件，按时间顺序排序。
    返回文件路径列表（按旧到新排序）。
    """
    all_files = []

    if not articles_dir.exists():
        return all_files

    # 获取归档目录路径
    archive_dir = get_archive_dir(articles_dir)

    # 遍历日期目录
    date_dirs = sorted(articles_dir.iterdir())
    for date_dir in date_dirs:
        if not date_dir.is_dir() or date_dir.name == "archived":
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


def main():
    """主函数。"""
    # 获取路径
    articles_dir = get_articles_dir()
    archive_dir = get_archive_dir(articles_dir)

    print(f"新闻目录: {articles_dir}", file=sys.stderr)
    print(f"归档目录: {archive_dir}", file=sys.stderr)

    # 扫描所有未归档文件
    all_files = scan_all_articles(articles_dir)
    print(f"扫描到文件总数: {len(all_files)}", file=sys.stderr)

    # 输出结果（JSON格式）
    result = {
        "articlesDir": str(articles_dir),
        "archiveDir": str(archive_dir),
        "totalFiles": len(all_files),
        "files": [str(f) for f in all_files]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if len(all_files) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())