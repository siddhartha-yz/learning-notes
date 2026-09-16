from pathlib import Path

import torch
from torchvision import transforms
from torchvision import datasets
from torch.utils.data import DataLoader
import torch.nn.functional as F
import torch.optim as optim

batch_size = 64
transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])

# 相对于本文件定位数据目录，不受终端或 IDE 的工作目录影响。
data_root = Path(__file__).resolve().parent.parent / 'dataset' / 'mnist'

train_dataset = datasets.MNIST(root=data_root, train=True, download=True, transform=transform)

train_loader = DataLoader(train_dataset, shuffle=True, batch_size=batch_size)

test_dataset = datasets.MNIST(root=data_root, train=False, download=True, transform=transform)

test_loader = DataLoader(test_dataset, shuffle=False, batch_size=batch_size)
