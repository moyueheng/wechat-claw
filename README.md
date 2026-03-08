1. 扫描 input/data/articles 目录（排除 archived 子目录）
2. 找出待分析的新闻（按文件名排序，旧文件在前）
3. 如果没有新闻需要分析，任务结束，除非用户主动要求分析
4. 分析所有待分析的新闻（1条就分析1条，2条就分析2条，以此类推）
5. 利用 .claude/skills/stock-analysis/SKILL.md 进行分析
6. 使用 .claude/skills/wechat-send-fixed-message/SKILL.md 通过微信把分析报告发送给某个人或者某个群
7. 将已分析的新闻文件移动到 input/data/articles/archived/YYYY-MM-DD/ 目录



1. 扫描 input/data/articles 目录（排除 archived 子目录）
2. 用 agent 找出待分析的新闻（按文件名排序，旧文件在前）
3. 如果没有新闻需要分析，任务结束，除非用户主动要求分析
4. 分析所有待分析的新闻（1条就分析1条，2条就分析2条，以此类推）
5. 利用 .claude/skills/stock-analysis/SKILL.md 进行分析
6. 使用 .claude/skills/wechat-send-fixed-message/SKILL.md 通过微信把分析报告发送给某个人或者某个群
7. 将已分析的新闻文件移动到 input/data/articles/archived/YYYY-MM-DD/ 目录