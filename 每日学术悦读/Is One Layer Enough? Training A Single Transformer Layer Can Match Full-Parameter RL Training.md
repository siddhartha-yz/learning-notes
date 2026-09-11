# Is One Layer Enough? Training A Single Transformer Layer Can Match Full-Parameter RL Training

__26.9.10__



这篇论文的核心可以压缩成一句话：

> **LLM 的 RL 后训练增益并不是均匀分布在所有 Transformer 层，而是高度集中在网络中部的一小部分层；甚至只训练一个中间层，就可能达到或超过全参数 RL。** ([arXiv](https://arxiv.org/html/2607.01232v2))

论文提出一个非常直接的实验：对于 $L$ 层 Transformer，每次只解冻第 $k$ 层，其余参数全部冻结，但梯度仍通过完整网络计算，然后进行 GRPO 等 RL 训练。定义“层贡献度”：

$\mathcal C(k)= \frac{S_k-S_{\text{base}}} {S_{\text{full}}-S_{\text{base}}}$

$\mathcal C=1$ 表示只训练这一层就恢复了全参数 RL 的全部增益；$\mathcal C>1$ 则说明单层训练反而超过全参数训练。([arXiv](https://arxiv.org/html/2607.01232v2))

最重要的发现有四个。

1. **不同层的 RL 学习能力差异极大。**
   Qwen3-1.7B 中最佳 Layer 10 达到 $\mathcal C=1.14$，即恢复了全参数 RL 的 **114%** 增益；最差只有 0.28。Qwen3-8B 的 Layer 16 达到 1.07，而 Layer 0 甚至是 **-0.51**，即只训练第一层会比原始模型还差。([arXiv](https://arxiv.org/html/2607.01232v2))
2. **高贡献层稳定集中在网络中间，大约 40%–60% 深度。**
   作者测试了 Qwen3、Qwen2.5、DeepSeek-R1-Distill-Qwen，1.5B–8B，GRPO / Dr.GRPO / GiGPO，以及数学、代码、Agent 任务，都出现了类似结构。七个模型的最佳单层全部达到或超过全参数训练。([arXiv](https://arxiv.org/html/2607.01232v2))
   你上传的讲解稿所概括的“中间 40%–60% 层承担绝大部分 RL 改进”基本就是论文最核心的结果。
3. **这是模型本身的结构属性，不太依赖具体训练数据。**
   同一个 Qwen3-1.7B：

- NuminaMath vs DeepScaleR：层排名 Spearman $\rho=0.76$
- 数学 NuminaMath vs 代码 DeepCoder：$\rho=0.59$

也就是说，某层在数学 RL 中很“能学”，换成代码 RL，它大概率仍然很“能学”。作者因此认为这种能力很大程度来自**预训练模型已经形成的内部层级结构**。([arXiv](https://arxiv.org/html/2607.01232v2))

1. **可以直接拿这个现象改进 RL 训练。**
   作者尝试了三种方法：提高高贡献层学习率、只训练高贡献层、完全不 profiling 而直接训练网络最中间几层。结果都能超过普通全参数 RL。比如 Qwen3-8B：

$\text{Full RL}=66.43$

只训练最佳 10 层：

$69.11$

直接凭位置选择中间层、不做逐层扫描，也能做到：

$68.19$

([arXiv](https://arxiv.org/html/2607.01232v2))

更有意思的是，论文发现这并不是因为“中间层参数变化得更多”。全参数 RL 时，各层权重变化幅度其实相当均匀；而单层训练时，高贡献层与低贡献层的参数变化幅度也差不多，但最终性能天差地别。([arXiv](https://arxiv.org/html/2607.01232v2))

所以作者更倾向于这样解释：

> **不同层的参数子空间，对 RL 信号的“可吸收能力”不同；中间层恰好处于一个特别适合用 RL 改写模型行为的参数子空间。**

还有一个很有意思的附带发现：不同高贡献层学到的东西并不相同。Top-7 单层模型新解决题目的平均 Jaccard 重合度只有 **34.1%**。在 OlympiadBench 上，把 7 个单层模型投票，准确率达到 **33.6%**，高于全参数 RL 的 26.9%，也高于对同一个全参数模型做 7 次采样 self-consistency 的 31.3%。说明不同层会形成具有互补性的“专家”。([arXiv](https://arxiv.org/html/2607.01232v2))

这篇论文真正重要的地方，不只是“少训练几层能省显存”，而是它改变了一个关于 RL 后训练的直觉：

**以前的直觉：**

$\text{RL improvement} \approx \text{全网络协同改变}$

**这篇论文提供的证据更接近：**

$\text{RL improvement} \approx \text{少数关键层吸收大部分行为更新}$

而且“哪些层适合吸收 RL”似乎在预训练结束时就已经基本形成。

不过目前不能把结论无限外推。作者只测试到 **8B**；layer-aware 训练策略目前主要在数学任务上验证；为什么偏偏是中间层，论文还没有给出理论解释，而且 $\mathcal C(k)$ 本身也依赖具体训练配置。作者在论文中明确把这些列为局限。([arXiv](https://arxiv.org/html/2607.01232v2))

所以我会把这篇论文记成：

> **RLHF/RLVR 不一定是在“重新训练整个 Transformer”，更可能是在预训练模型已有表示空间里，重点调整少数中间层，从而改变推理与行为策略。**

对于理解 **LoRA、参数高效 RL、模型内部功能分层**，这篇论文的结果很值得关注。