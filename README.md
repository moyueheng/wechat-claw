1. 读取 memory/news-analysis-state.json 获取上次分析的最后文件
2. 扫描 input/data/articles 目录
3. 找出新增的新闻（按文件名排序，新文件在后）， 如果没有新增新闻就不要分析， 这个任务就结束了， 除非用户主动要求分析
4. 分析所有新增的新闻（1条就分析1条，2条就分析2条，以此类推）
5. 利用 .claude/skills/stock-analysis/SKILL.md 进行分析
6. .claude/skills/wechat-send-fixed-message/SKILL.md 通过微信把分析报告发送给 某个人或者某个群



1. 读取 memory/news-analysis-state.json 获取上次分析的最后的时间点
2. 用 agent 
3. 找出新增的新闻（按文件名排序，新文件在后）， 如果没有新增新闻就不要分析， 这个任务就结束了， 除非用户主动要求分析
4. 分析所有新增的新闻（1条就分析1条，2条就分析2条，以此类推）
5. 利用 .claude/skills/stock-analysis/SKILL.md 进行分析
6. .claude/skills/wechat-send-fixed-message/SKILL.md 通过微信把分析报告发送给 某个人或者某个群
7. 更新 memory/news-analysis-state.json