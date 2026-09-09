# 答题记录

每次填写答案并点击提交后，应用在本目录按 UTC 日期创建独立 JSON，保留题目快照（含评分要求）、本题命令历史与输出、原始答案、本地检查项、提交时间和评审结果。修改答案重新提交会生成新记录。仅运行命令而没有提交的会话不保存；重置前请提交以保留记录。

状态说明：`submitted` 表示已保存但尚无评审结果（可能中途退出），`api_not_configured` 表示未配置 API，`api_error` 表示调用失败，`reviewed` 表示已返回评审。只有 `reviewed` 且 `passed: true` 才表示本次通过。

不保存 API 地址、密钥或请求头。当前配置的密钥若误贴到答案中会被替换。记录保存在 Git 仓库内，下次运行原有 `note` 命令会连同题目与代码一起提交和推送；应用不会在每次答题时自动执行 Git。

`legacy-progress-2026-09-08.json` 是从旧版本地进度导入的历史摘要，包含三题的通过结果与评语；旧版没有留下原始答案和操作历史，不能将摘要视为完整日志。模型评语也是待复核的数据，不等于真实执行记录。

PyTorch 记录使用 schema_version=2，区分 `pytorch_run`（真实本地测试）和 `pytorch_submission`（提交 Agent）。包含代码、运行前预测、解释、提示层级和测试结果。`tested` 仅表示完成本地测试，不能等同于 Agent 评审通过。

PyTorch 教学实验使用 `kind=pytorch_tutorial_run`，记录教学快照、实际运行代码与输出；`local_result.passed` 仅表示代码执行成功，顶层 `passed=false`，不计入题目通过。它与练习测试、Agent 正式评审分开统计。
