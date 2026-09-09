"""Self-study regression references; not displayed by the exercise UI."""
import unittest
from torch_engine import run_code, RUNTIME

SOLUTIONS = {
 'torch-batch': 'def build_batch(features, labels):\n    return torch.tensor(features,dtype=torch.float32),torch.tensor(labels,dtype=torch.int64)',
 'torch-flatten': 'def flatten_images(images):\n    return images.reshape(images.shape[0],-1)',
 'torch-center': 'def center_features(X):\n    m=X.mean(dim=0)\n    return X-m,m',
 'torch-probs': 'def class_probabilities(logits):\n    return torch.softmax(logits,dim=1)',
 'torch-select': 'def target_probabilities(probs,targets):\n    return probs[torch.arange(probs.shape[0]),targets]',
 'torch-mask': 'def masked_token_mean(token_losses,valid):\n    return token_losses[valid].mean()',
}
WRONG = {
 'torch-batch': 'def build_batch(features, labels):\n    return torch.tensor(features),torch.tensor(labels,dtype=torch.float32)',
 'torch-flatten': 'def flatten_images(images):\n    return images.reshape(-1)',
 'torch-center': 'def center_features(X):\n    m=X.mean(dim=1)\n    return X-m,m',
 'torch-probs': 'def class_probabilities(logits):\n    return torch.softmax(logits,dim=0)',
 'torch-select': 'def target_probabilities(probs,targets):\n    return probs[:,targets]',
 'torch-mask': 'def masked_token_mean(token_losses,valid):\n    return token_losses.mean()',
}

@unittest.skipUnless((RUNTIME / 'bin/python').exists(), '运行 setup-torch.sh 后测试真实 PyTorch')
class TorchTests(unittest.TestCase):
    def test_all_reference_implementations(self):
        for name, code in SOLUTIONS.items():
            with self.subTest(name=name):
                result = run_code(name, 'import torch\n' + code)
                self.assertTrue(result['passed'], result)
                self.assertGreaterEqual(len(result['cases']), 3)

    def test_common_misconceptions_fail(self):
        for name, code in WRONG.items():
            with self.subTest(name=name):
                result = run_code(name, 'import torch\n' + code)
                self.assertFalse(result['passed'])
                self.assertTrue(any(not case['passed'] for case in result['cases']))

    def test_inplace_mutation_is_rejected(self):
        result = run_code('torch-center', 'import torch\ndef center_features(X):\n    m=X.mean(dim=0)\n    X-=m\n    return X,m')
        self.assertFalse(result['passed'])

    def test_execution_error_is_not_success(self):
        result = run_code('torch-mask', 'def masked_token_mean(:\n    pass')
        self.assertFalse(result['passed'])
        self.assertIn('SyntaxError', result['cases'][0]['detail'])

    def test_host_home_and_credentials_are_not_mounted(self):
        code = '''import torch
from pathlib import Path
assert not Path('/home/yang-zhi').exists()
assert not Path('/root/.local/state/learning-notes-lab/credentials.json').exists()
'''+SOLUTIONS['torch-batch']
        self.assertTrue(run_code('torch-batch', code)['passed'])

if __name__ == '__main__': unittest.main()
