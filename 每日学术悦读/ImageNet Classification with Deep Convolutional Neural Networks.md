# ImageNet Classification with Deep Convolutional Neural Networks
__26.9.12__

把 AlexNet 原论文和两份李沐精读合起来，可以压缩成下面这套笔记。

## AlexNet：核心总结

**一句话：AlexNet 证明了——只要有足够大的数据、足够大的 CNN、GPU 算力和合适的训练技巧，神经网络可以直接从原始像素中学习特征，并大幅击败传统计算机视觉方法。**

2012 年以前，计算机视觉主流还是「人工设计特征（SIFT 等）→ 分类器」。AlexNet 则直接把 RGB 像素输入 CNN，端到端完成特征学习和分类。论文在约 120 万张、1000 类的 ImageNet 上训练约 6000 万参数的网络，并取得远超此前方法的结果。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

### 1. 网络到底长什么样

AlexNet 本质上就是：

```text
224×224×3 RGB 图像
    ↓
Conv 11×11, 96, stride=4
    ↓
MaxPool
    ↓
Conv 5×5, 256
    ↓
MaxPool
    ↓
Conv 3×3, 384
    ↓
Conv 3×3, 384
    ↓
Conv 3×3, 256
    ↓
MaxPool
    ↓
FC 4096
    ↓
FC 4096
    ↓
FC 1000
    ↓
Softmax
```

即 **5 个卷积层 + 3 个全连接层**。卷积部分不断压缩空间尺寸、增加通道数，可以粗略理解成：

> 空间信息越来越少，抽象语义特征越来越丰富。

原论文完整架构就是这个思路，只不过因为当时两张 GTX 580 每张只有 3 GB 显存，被强行拆到两张 GPU 上，所以原始结构图显得异常复杂。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf)) 李沐也特别强调：这个双 GPU 切法更多是当年的工程限制，不是 AlexNet 今天最值得学习的东西。

### 2. AlexNet 真正用了哪些关键技术

首先是 **ReLU**：

$\operatorname{ReLU}(x)=\max(0,x)$

相比当时常见的 sigmoid/tanh，AlexNet 发现 ReLU 能让深层网络训练快很多。原论文甚至报告一个实验：达到相同训练误差时，ReLU 比 tanh 快约 6 倍。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

然后是 **GPU 训练**。这不是单纯「拿 GPU 加速一下」，而是 GPU 终于使大规模 CNN 变得实际可训练。AlexNet 本身需要两块 GTX 580 3GB，完整训练约 **5–6 天**。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

其次是几个防过拟合手段：

- 数据增强：随机裁剪、水平翻转、RGB 颜色扰动；
- Dropout：前两个 4096 维全连接层随机丢弃 50% 神经元；
- weight decay。

尤其 Dropout 使一个巨大的全连接网络不至于严重过拟合。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

训练本身其实很「现代」：

```text
Optimizer: SGD
Batch size: 128
Momentum: 0.9
Weight decay: 0.0005
Initial LR: 0.01
约 90 epochs
```

验证误差不再下降时，人工把学习率除以 10。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

还有两个今天已经没那么重要的设计：

**LRN（Local Response Normalization）\**和\**Overlapping Pooling**。当年实验确实带来了几个百分点以内的提升，但李沐精读中特别指出，LRN 后来基本被淘汰，更现代的归一化方法取代了它。

------

## 3. 它到底强到了什么程度？

ILSVRC-2010：

| 方法                 | Top-1 error | Top-5 error |
| -------------------- | ----------- | ----------- |
| SIFT + Fisher Vector | 45.7%       | 25.7%       |
| **AlexNet**          | **37.5%**   | **17.0%**   |

2012 年比赛最终系统的 **Top-5 error = 15.3%**，第二名则是 **26.2%**。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

这不是「提升了零点几个百分点」，而是断层式领先。

所以 AlexNet 的影响不是：

> 「又提出了一种新的 CNN。」

而更像：

> **它用实验告诉整个计算机视觉界：这条技术路线真的能赢。**

李沐的第一份精读也把论文最直接的卖点概括为：「训练一个非常大的神经网络，然后结果比第二名好非常多。」

------

## 4. 更深一层：AlexNet 真正奠基的东西

我认为你现在读这篇论文，最该抓住的不是 LRN、池化参数甚至具体的 11×11 卷积，而是下面三个思想。

### 第一，端到端特征学习

传统 CV：

```text
图片
↓
人工设计 SIFT/HOG 等特征
↓
分类器
```

AlexNet：

```text
原始 RGB
↓
CNN 自己学习特征
↓
分类
```

论文只是很平淡地写「我们在中心化后的 raw RGB values 上训练」，但李沐认为这其实是后来深度学习最核心的价值之一：**不用人手工规定机器应该看什么特征。**

### 第二，深度网络学出来的是「语义表示」

这是论文里一个非常容易被忽略、但极其重要的实验。

AlexNet 把一张图经过网络后，变成倒数第二层的 **4096 维向量**。

然后比较两个向量的距离：

$\|\mathbf z_1-\mathbf z_2\|_2$

结果发现向量接近的图片，在语义上通常也接近：

```text
狗 → 找回来各种姿态的狗
大象 → 找回来各种姿态的大象
花 → 找回来相似的花
```

即使它们原始像素完全不相似。原论文明确展示了这个现象。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

李沐甚至认为，这可能是论文里**意义最大的结果之一**：深度网络把像素转换成了具有语义结构的表示空间。

这其实已经非常接近你后来学到的：

```text
image → embedding
text → embedding
audio → embedding
```

乃至今天多模态模型里的 representation learning。

### 第三，Scaling 思想已经出现

AlexNet 最后的判断非常有意思：

> 更大的网络、更长的训练、更好的 GPU、更大的数据集，应该还能继续提高性能。

他们甚至直接说，当时模型大小主要受限于 **GPU 内存和能忍受的训练时间**。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))

这和十多年后的：

> data ↑ + compute ↑ + model ↑ → capability ↑

实际上已经有明显的思想连续性。

------

## 5. 哪些东西活到了今天，哪些已经过时？

可以直接这样记：

| AlexNet 元素            | 今天怎么看                  |
| ----------------------- | --------------------------- |
| CNN / 深层网络          | **核心思想保留**            |
| 原始数据端到端学习      | **极其重要**                |
| Representation Learning | **极其重要**                |
| ReLU                    | **保留，影响巨大**          |
| GPU 训练                | **成为基础设施**            |
| Data Augmentation       | **仍然重要**                |
| SGD + Momentum          | **仍然重要**                |
| Weight Decay            | **仍然重要**                |
| Dropout                 | **仍在使用，但地位下降**    |
| LRN                     | **基本淘汰**                |
| Overlapping Pooling     | **不再是核心技术**          |
| 两张 GPU 特殊切网络     | **实现方式淘汰**            |
| 4096+4096 巨型 FC       | **现代 CNN 通常不用这么干** |
| 手工观察 val 再 LR÷10   | **被 scheduler 等取代**     |
| 特定 bias 初始化为 1    | **基本成为历史细节**        |

李沐对整篇论文的评价很准确：**AlexNet 很像一份「我把这些东西组合起来，结果特别好」的技术报告，很多地方讲了 what，却没真正解释 why。** 后来十几年大量研究才逐渐弄清哪些组件是真正重要的，哪些只是当时有效的 engineering trick。

------

## 6. 你现在学习 AlexNet，最终只需记住这张图

```text
大数据 ImageNet
       +
大容量 CNN
       +
GPU 算力
       +
ReLU / SGD
       +
数据增强 / Dropout
       ↓
可以直接从 raw pixels
学习层级化语义特征
       ↓
大幅击败人工特征方法
       ↓
深度学习时代真正爆发
```

所以 AlexNet 的历史意义并不是「发明了 CNN」——CNN 早就存在；ReLU、Dropout 等也并非全由这篇论文首次提出。

**它真正完成的是一次系统性证明：深度神经网络 + 大数据 + 大算力 + 端到端表示学习，这条路线是可行的，而且能够碾压当时的主流方法。**

这也是为什么今天看 AlexNet 的具体网络已经非常古老，但这篇论文仍然是深度学习历史中最重要的节点之一。([NIPS 会议论文](https://papers.nips.cc/paper/4824-imagenet-classification-with-deep-convolutional-neural-networks.pdf))