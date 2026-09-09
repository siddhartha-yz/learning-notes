# PyTorch 第一阶段验证

本记录是开发验证，不是学生作答。第一阶段六题分别覆盖批次构造、图像展平、按特征中心化、类别概率、配对索引、有效 token 平均损失。

## 执行证据

- CPU PyTorch 2.14.0+cpu，系统 Python 3.14；专用虚拟环境与 GTK 环境分离。
- 六份参考实现通过实际张量测试，验证形状、dtype、数值与输入保持。测试按题目契约包含 B=1、非方形批次、float64、非连续张量、极大 logits、不等长序列和只有一个有效token等情况。
- 六类典型错误均被拒绝：标签dtype错误、展平batch、沿错误轴求均值、跨样本softmax、取整列而非配对索引、把padding纳入平均。
- 原地修改输入、Python语法错误也被拒绝。隔离环境不能看到用户Home与凭据路径。
- 合并 Linux 回归共37项 unittest 通过（PyTorch测试不是跳过状态）。

## 桌面验证

`pytorch_ui_smoke.py` 以六份真实可执行实现走通界面：预测不能为空、默认无API提示、主动提示层级、代码运行、测试反例展示入口、模拟Agent拒绝再通过、代码修改后的重跑要求、六次运行与七次正式提交日志、草稿恢复、课程切换、全部完成提示。

所有测试使用临时状态与记录目录，未覆盖用户已有草稿、成绩或答题日志。Agent返回用模拟结果，未调用用户实际模型API。六道题的PyTorch数值验证是真实执行。

`ui_smoke.py` 同时验证原有 Linux 六题流程、API设置恢复与按章导航。已查看 PyTorch 页面实际窗口截图，确认题目、预测、代码、测试结果、解释和提交入口可用。

复现：

```bash
./practice-lab/setup-torch.sh
python3 -m unittest discover -s practice-lab -v
python3 practice-lab/ui_smoke.py
python3 practice-lab/pytorch_ui_smoke.py
```

限制：不是针对恶意学生代码的防作弊评测系统；隔离用于避免运行练习时触及个人文件。当前通过记录只代表一次成功提交，不等于长期熟练度。
