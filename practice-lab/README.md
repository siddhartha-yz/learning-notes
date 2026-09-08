# 学习笔记 · 实践工坊

基于 `Linux系统学习/26.9.3.md` 的 Linux 原生桌面示范。三个约 5–10 分钟的小任务形成 CIFAR-10 训练前检查流程：定位项目与数据、发现隐藏配置、检查模型检查点。只涉及当天的 `ls`、`cd`、`pwd`，无需 GPU、真实数据集或机器学习依赖。

## 启动

在仓库根目录执行：

```bash
./practice-lab/launch.sh
```

Ubuntu / Debian 依赖（当前开发电脑已有）：

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 bubblewrap
```

需要图形桌面及允许 bubblewrap 用户命名空间的 Linux。隔离不可用时拒绝执行，不降级为宿主机终端。

## 使用

1. 选择题目，阅读任务；可打开对应原始笔记或查看提示。
2. 在应用的命令输入框输入命令并按 Enter。输出来自真实 Bash / GNU 工具，当前目录会延续。
3. 在“观察与解释”中填写你的发现和理由。
4. 打开 API 设置，填写兼容 OpenAI Chat Completions 的 HTTPS Base URL、模型名和密钥。Base URL 保留服务商所需前缀（如 `/v1`），应用自动追加 `/chat/completions`。
5. 提交给 Agent。命令证据检查与模型评审均满足后才通过；缺少配置、网络失败或响应无效均不会标记通过。

密钥只在内存中保留，也可通过 `LEARNING_LAB_API_KEY` 环境变量提供。模型名与地址保存在 `$XDG_STATE_HOME/learning-notes-lab/api.json`，默认是 `~/.local/state/learning-notes-lab/api.json`；进度保存在同目录 `progress.json`。密钥不写入 Git；提交记录保存在仓库内的 `practice-lab/attempts/`，会随 `note` 命令上传。提交会向你指定的服务发送当前题目、最多最近 80 条练习命令及输出、你的解释；不上传整个笔记仓库。

## 本版终端范围

这是针对本课的逐条命令练习终端，不是完整交互式 shell：支持 `ls`、`cd`、`pwd` 和 `~` 路径；不支持管道、变量、重定向、Tab 补全及全屏程序。命令参数由 `shlex` 解析并重新转义，宿主机 Home、密钥和仓库不挂载进练习环境。练习文件只读，无网络，执行限时 4 秒。切题或重置会新建临时环境、清空命令记录；评审结果保留在本机。

检查点为 0、12 MiB 和 24 MiB 的稀疏占位文件，因此列表中的 `total` 可能为 0，这是实际占用块数，不是文件逻辑大小。题目不要求判断 `total`，也不能将占位文件加载为模型。

## 判题与扩展

- `lessons.json`：题目、知识来源、提示、解释评分要求及命令证据检查。
- `core.py`：临时环境、隔离命令执行、本地检查、API 评审和本机状态保存。
- `app.py`：GTK 桌面交互。
- `test_core.py`：真实命令与隔离回归测试、模拟 API 响应及错误测试。

新题可以追加到 JSON；需要新数据或新检查类型时扩展 `Session` 和 `checks`。本版没有自动从新增笔记生成题目，先将这组高质量人工题作为内容标准。模型只返回评审，不拥有本机工具执行权限；命令证据检查不完全替代理解判断，API 的 `passed` 也不单独决定通过。

请求格式参考 [OpenAI Chat Completions 官方文档](https://developers.openai.com/api/reference/resources/chat)。兼容服务需要支持 `messages` 和文本 JSON 输出，未强制要求 JSON schema 功能。

## 验证

```bash
python3 -m unittest discover -s practice-lab -v
```

自动测试覆盖正向完成、错误路径、隐藏文件、文件大小、返回 Home、命令限制、宿主机路径隔离、API 请求结构、401、无效返回和状态文件权限。真实服务连通性需填写自己的 API 配置后验证；测试不消耗模型额度。

## 设计取舍与后续

先使用本机已有的 GTK，避免为三道题引入浏览器服务和完整前端构建链。教学内容、执行器与界面分离，后续可扩展章节、命令历史、渐进提示、复习队列以及更完整的容器终端。原有 `note` 命令仍按原流程上传仓库内容。

可选：执行 `python3 practice-lab/install-launcher.py` 将当前仓库注册到应用菜单，搜索“实践工坊”即可启动。仓库移动后重新执行即可更新路径。

评审通过时只显示固定的通过提示，不追加拓展思考；未通过时只指出本题需要修正的内容。答题日志格式见 [答题记录说明](./attempts/README.md)。
