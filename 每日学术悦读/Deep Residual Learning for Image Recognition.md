# Deep Residual Learning for Image Recognition

__26.9.13__

> **ResNet 解决的核心问题不是“网络深了会过拟合”，而是“网络深到一定程度后，明明存在不差于浅层网络的解，SGD 却很难找到它”。**

### 1. ResNet 在解决什么问题？

理论上，更深的网络表达能力至少不应该比浅网络差。

假设一个 20 层网络效果很好，那么构造一个 34 层网络时，新增的 14 层只需要全部实现：

$H(x)=x$

即 identity mapping，那么 34 层至少应该和 20 层一样好。

但实验发现：

$\text{更深 plain network} \rightarrow \text{训练误差反而更高}$

这叫 **degradation problem（退化问题）**。

关键是：它不是普通的过拟合。因为如果是过拟合，应该出现

$\text{train error}\downarrow,\quad \text{test error}\uparrow$

实际却是训练误差和测试误差一起变差。ResNet 原文正是从这个反常现象出发。([CVF Open Access](https://openaccess.thecvf.com/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper?utm_source=chatgpt.com)) 你上传的精读也特别强调了这一点。

------

### 2. 核心思想：不要直接学 $H(x)$

普通网络让若干层直接学习：

$H(x)$

ResNet 改成学习它相对于输入 $x$ 的“残差”：

$F(x)=H(x)-x$

于是：

$H(x)=F(x)+x$

所以一个 Residual Block 就是：

$\boxed{y=F(x)+x}$

其中：

- $F(x)$：卷积层真正学习的东西；
- $x$：通过 shortcut 原样绕过去；
- 最后把二者相加。

原论文的假设非常朴素：

> 如果最优解接近 identity mapping，让网络学习 $F(x)\approx0$，可能比让很多非线性层自己拟合 $H(x)=x$ 更容易。 ([CVF Open Access](https://openaccess.thecvf.com/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper.pdf?utm_source=chatgpt.com))

也就是原来要网络费劲学：

$H(x)=x$

现在直接送给它一个 $x$，网络只需要学：

$F(x)=0$

这就是 ResNet 最核心的思想。

------

### 3. Shortcut 为什么如此重要？

最简单的 shortcut：

$y=F(x)+x$

没有额外可学习参数，额外计算基本只有一次逐元素加法。因此它几乎不增加模型复杂度。([CVF Open Access](https://openaccess.thecvf.com/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper?utm_source=chatgpt.com))

如果 $F(x)$ 与 $x$ 维度不同，则用投影：

$y=F(x)+W_sx$

通常就是用 $1\times1$ 卷积改变通道数和空间尺寸。

------

### 4. 从今天来看，为什么 ResNet 特别容易训练？

这里要区分：

**原论文自己的解释**主要是“优化 residual 比直接优化 mapping 更容易”。

后来更常见的解释是 **gradient flow**。

普通深层网络：

$y=F(x)$

反向传播会产生大量 Jacobian 连乘：

$\frac{\partial y}{\partial x} = \prod_i \frac{\partial F_i}{\partial x}$

非常深时容易让梯度越来越弱。

Residual block：

$y=x+F(x)$

所以：

$\frac{\partial y}{\partial x} = I+\frac{\partial F(x)}{\partial x}$

这里关键就是那个：

$\boxed{I}$

即使 $\partial F/\partial x$ 很小，还有 identity path 让梯度直接传播。

所以可以把 shortcut 同时理解成：

**前向传播高速公路：**

$x\rightarrow x$

**反向传播高速公路：**

$\nabla y\rightarrow\nabla x$

李沐的精读后半段也主要用这个角度解释为什么 ResNet 更容易训练。

但要注意：**这更多是后来的理解，不能说原始 ResNet 论文已经严格证明了梯度机制。**

------

### 5. ResNet 的两个基本 block

ResNet-18 / 34 使用 Basic Block：

$3\times3 \rightarrow 3\times3$

然后：

$F(x)+x$

而 ResNet-50 / 101 / 152 使用 Bottleneck：

$1\times1 \rightarrow 3\times3 \rightarrow 1\times1$

直觉是：

$256 \rightarrow 64 \rightarrow 64 \rightarrow 256$

先用 $1\times1$ 降维，再进行昂贵的 $3\times3$ 卷积，最后升维。

这样可以把网络做得非常深，同时避免计算量爆炸。

所以：

- ResNet-18/34：Basic Block
- ResNet-50/101/152：Bottleneck

这个区别很重要。

------

### 6. 最关键的实验

论文做了一个非常有说服力的对照：

Plain-18 vs Plain-34：

$\text{Plain-34} < \text{Plain-18}$

网络更深，反而更差。

加入 residual connection：

$\text{ResNet-34} > \text{ResNet-18}$

于是作者证明：

> 问题不是“34 层网络没有表达能力”，而是普通结构难以优化；Residual Learning 改变了优化问题。

精读里的训练曲线还能看到，加入 residual 后 34 层网络不仅最终结果更好，而且下降得明显更快。

------

### 7. 最终结果为什么震撼

作者一路做到 **ResNet-152**。

它：

- 深度约为 VGG-19 的 8 倍；
- 计算复杂度反而低于 VGG；
- ImageNet ensemble top-5 error 达到 **3.57%**；
- 获得 ILSVRC 2015 classification 第一；
- 同时在 detection、localization、COCO detection、segmentation 等项目取得第一。([arXiv](https://arxiv.org/abs/1512.03385?utm_source=chatgpt.com))

在 CIFAR-10 上甚至实验了百层乃至千层级网络。([arXiv](https://arxiv.org/abs/1512.03385?utm_source=chatgpt.com))

所以 ResNet 真正证明了：

$\boxed{\text{网络做到极深，是可以稳定训练的}}$

------

### 8. ResNet 真正的历史意义

ResNet 并不是第一个提出 shortcut connection 的工作，论文自己也讨论了 Highway Networks 等相关工作。

它真正厉害的地方是：

> **用极其简单的 identity shortcut，解决了当时深度网络最核心的优化问题，并通过大规模实验证明“更深”可以真正转换为更好的性能。**

所以 ResNet 的价值并不是：

> “发明了一条连线。”

而是：

$\boxed{ \text{把 identity path 变成了深层网络的一种基本结构原则} }$

今天 Transformer 里的 residual connection：

$x+\operatorname{Attention}(x)$$x+\operatorname{MLP}(x)$

本质上也继承了这种思想。

------

如果只记住 **3 句话**：

1. **问题：**深层 plain network 出现 degradation，SGD 难以找到本应存在的好解。
2. **方法：**

$\boxed{H(x)=F(x)+x}$

让网络学习 residual，而不是完整映射。

1. **意义：**shortcut 同时改善优化和梯度传播，使数十、数百乃至上千层网络真正变得可训练。

我认为你现在读 ResNet，最应该抓住的不是具体 ResNet-50 的层数表，而是这个思想：

$\boxed{\text{不要强迫新增层必须做有用的事情；给它一条“什么都不做”的简单路径。}}$

**如果新增变换有用，就学 $F(x)$；如果没用，就让 $F(x)\approx0$。**

这就是 ResNet 最漂亮的地方。