"""Execute all teaching snippets and their meaningful modifications in isolation."""
import json
from pathlib import Path
import unittest
from torch_engine import run_code

TUTORIALS = json.loads((Path(__file__).parent / 'pytorch/tutorials.json').read_text())


class TutorialTests(unittest.TestCase):
    def test_examples_and_transfer_observations(self):
        changes = {
            'torch-batch': ('[[0.5, 2.0, 7.0], [1.5, 4.0, 8.0]]', '[[0.5, 2.0, 7.0]]', '(1, 3)'),
            'torch-flatten': ('start_dim=1', 'start_dim=0', '(12,)'),
            'torch-center': ('mean = x.mean(dim=0)', 'mean = x.mean(dim=1)', 'RuntimeError'),
            'torch-probs': ('dim=1', 'dim=0', '各类概率'),
            'torch-select': ('[2, 0]', '[1, 1]', '0.3000, 0.1000'),
            'torch-mask': ('90.', '9000.', 'tensor(6.)'),
        }
        for id, tutorial in TUTORIALS.items():
            with self.subTest(id=id):
                result = run_code(id, tutorial['code'], tutorial=True)
                self.assertTrue(result['passed'], result)
                self.assertTrue(result['stdout'])
                self.assertEqual(result['cases'], [])
                old, new, expected = changes[id]
                modified = tutorial['code'].replace(old, new)
                if id == 'torch-probs':
                    modified += '\nassert torch.allclose(probs.sum(dim=0), torch.ones(3))\nassert not torch.allclose(probs.sum(dim=1), torch.ones(2))\n'
                result = run_code(id, modified, tutorial=True)
                self.assertEqual(result['passed'], id != 'torch-center', result)
                self.assertIn(expected, result['stdout'] + result['error'])

    def test_error_and_output_limit(self):
        for code in ['x =', 'raise SystemExit(1)']:
            result = run_code('torch-batch', code, tutorial=True)
            self.assertFalse(result['passed'])
            self.assertTrue(result['error'])
        result = run_code('torch-batch', 'print("x" * 20000)', tutorial=True)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['stdout']), 12000)


if __name__ == '__main__': unittest.main()
