"""Executed only inside the exercise sandbox with the dedicated torch runtime."""
import contextlib
import copy
import io
import json
from pathlib import Path
import resource
import sys
import traceback

resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
import torch

torch.set_num_threads(1)
torch.manual_seed(713)


class BoundedOutput(io.TextIOBase):
    def __init__(self):
        self.text = ''
    def write(self, value):
        self.text += value[:max(0, 12000 - len(self.text))]
        return len(value)
    def flush(self):
        pass


def cases(lesson):
    if lesson == 'torch-batch':
        for name, b, d in [('示例批次', 3, 2), ('单样本仍保留批次轴', 1, 4), ('非方形批次', 4, 3)]:
            x = [[i * d + j + 0.25 for j in range(d)] for i in range(b)]
            y = [i % 3 for i in range(b)]
            yield name, (x, y), (torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.int64))
    elif lesson == 'torch-flatten':
        for name, shape, transpose in [('两张多通道图像', (2, 3, 2, 2), False),
                                       ('单图保留batch', (1, 2, 3, 4), False),
                                       ('非连续图像与新批大小', (3, 2, 2, 4), True)]:
            x = torch.arange(torch.tensor(shape).prod().item(), dtype=torch.float64).reshape(shape)
            if transpose: x = x.transpose(2, 3)
            expected = torch.stack([sample.reshape(-1) for sample in x])
            yield name, (x,), expected
    elif lesson == 'torch-center':
        for name, x in [('特征尺度不同', torch.tensor([[1., 10.], [3., 30.]])),
                        ('B不等于D', torch.tensor([[1., 10., -4.], [5., 30., 8.]])),
                        ('单样本中心化', torch.tensor([[5., 20., 9.]], dtype=torch.float64)),
                        ('非连续输入', torch.arange(12, dtype=torch.float64).reshape(3, 4).T)]:
            mean = torch.stack([x[:, i].sum() / len(x) for i in range(x.shape[1])])
            yield name, (x,), (x - mean, mean)
    elif lesson == 'torch-probs':
        for name, x in [('均匀分数', torch.zeros(2, 2)), ('区分类别轴与批次轴', torch.tensor([[1., 2., 3.], [-1., 4., 0.]])),
                        ('单样本', torch.tensor([[2., -1., 0.]], dtype=torch.float64)),
                        ('单类别', torch.tensor([[2.], [7.]])),
                        ('大分数不能溢出', torch.tensor([[1000., 1001., 999.], [-1000., -998., -999.]]))]:
            yield name, (x,), torch.softmax(x, dim=1)
    elif lesson == 'torch-select':
        for name, x, y in [('配对而非整列', torch.tensor([[.1, .7, .2], [.6, .3, .1]]), torch.tensor([1, 0])),
                          ('单样本输出不是标量', torch.tensor([[.25, .75]]), torch.tensor([1])),
                          ('非连续概率与多类别', torch.softmax(torch.arange(12, dtype=torch.float64).reshape(3, 4).T, 1).T, torch.tensor([0, 2, 1]))]:
            # Normalize rows while retaining non-contiguous layout in the last case.
            if name.startswith('非连续'):
                x = torch.softmax(torch.arange(12, dtype=torch.float64).reshape(3, 4), 1).T.contiguous().T
            yield name, (x, y), torch.stack([x[i, int(y[i])] for i in range(len(y))])
    elif lesson == 'torch-mask':
        for name, x, valid in [
            ('不等长句按token等权', torch.tensor([[1., 3., 100.], [8., 100., 100.]]), torch.tensor([[True, True, False], [True, False, False]])),
            ('一个有效token', torch.tensor([[1e6, 7., 1e6]], dtype=torch.float64), torch.tensor([[False, True, False]])),
            ('全部有效', torch.tensor([[2., 4.], [6., 8.]]), torch.ones(2, 2, dtype=torch.bool)),
            ('非连续序列', torch.arange(1, 7, dtype=torch.float64).reshape(2, 3).T, torch.tensor([[True, False], [True, True], [False, True]]))]:
            selected = [x[i, j] for i in range(x.shape[0]) for j in range(x.shape[1]) if valid[i, j]]
            yield name, (x, valid), torch.stack(selected).sum() / len(selected)
    else:
        raise ValueError('未知题目')


FUNCTIONS = {'torch-batch': 'build_batch', 'torch-flatten': 'flatten_images',
             'torch-center': 'center_features', 'torch-probs': 'class_probabilities',
             'torch-select': 'target_probabilities', 'torch-mask': 'masked_token_mean'}


def compare(actual, expected):
    if isinstance(expected, tuple):
        if not isinstance(actual, (tuple, list)) or len(actual) != len(expected):
            raise AssertionError('需要返回指定数量的张量组成的 tuple/list')
        for a, e in zip(actual, expected): compare(a, e)
    else:
        if not isinstance(actual, torch.Tensor):
            raise AssertionError(f'应返回 Tensor，实际为 {type(actual).__name__}')
        torch.testing.assert_close(actual, expected, rtol=1e-5, atol=1e-6, check_dtype=True)


def unchanged(after, before):
    if isinstance(before, torch.Tensor):
        torch.testing.assert_close(after, before, rtol=0, atol=0)
    elif isinstance(before, (tuple, list)):
        if len(after) != len(before): raise AssertionError('输入长度被修改')
        for a, b in zip(after, before): unchanged(a, b)
    elif after != before:
        raise AssertionError('输入数据被修改')


def run(lesson, source):
    captured = BoundedOutput()
    results = []
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        try:
            namespace = {'__name__': 'submission'}
            exec(compile(source, 'submission.py', 'exec'), namespace)
            fn = namespace.get(FUNCTIONS[lesson])
            if not callable(fn): raise ValueError('缺少要求的函数：' + FUNCTIONS[lesson])
            for name, args, expected in cases(lesson):
                before = copy.deepcopy(args)
                actual = None
                try:
                    actual = fn(*args)
                    compare(actual, expected)
                    unchanged(args, before)
                    detail = '形状、dtype、数值与输入保持检查通过'
                    passed = True
                except Exception as exc:
                    passed = False
                    detail = f'{type(exc).__name__}: {exc}'[:2000]
                results.append(dict(name=name, passed=passed, detail=detail,
                                    inputs=repr(before)[:2500], expected=repr(expected)[:2000], actual=repr(actual)[:2000]))
        except Exception:
            results.append(dict(name='加载实现', passed=False, detail=traceback.format_exc()[-3000:]))
    return dict(torch_version=torch.__version__, passed=bool(results) and all(r['passed'] for r in results),
                cases=results, stdout=captured.text)


def run_demo(source):
    captured = BoundedOutput()
    error = ''
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        try:
            exec(compile(source, 'teaching.py', 'exec'), {'__name__': '__main__'})
        except BaseException:
            error = traceback.format_exc()[-3000:]
    return dict(mode='tutorial', torch_version=torch.__version__, passed=not error,
                cases=[], stdout=captured.text, error=error)


if __name__ == '__main__':
    source = Path('/submission/code.py').read_text()
    result = run_demo(source) if sys.argv[1] == '--tutorial' else run(sys.argv[1], source)
    Path('/work/result.json').write_text(json.dumps(result, ensure_ascii=False))
