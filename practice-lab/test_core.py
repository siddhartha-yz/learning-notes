import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import urllib.error
from core import Session, LESSONS, checks, review, save_json


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.session = Session()

    def tearDown(self):
        self.session.close()

    def run_commands(self, commands):
        for command in commands:
            self.session.run(command)

    def test_lesson_one_and_wrong_relative_path(self):
        self.run_commands(['pwd', 'ls projects/cifar10', 'cd projects/cifar10', 'pwd'])
        self.assertNotEqual(self.session.run('ls datasets/cifar10')['exit_code'], 0)
        self.session.run('ls /datasets/cifar10')
        self.assertTrue(all(ok for _, ok in checks(LESSONS[0], self.session)))

    def test_hidden_and_empty_submission(self):
        self.assertFalse(any(ok for _, ok in checks(LESSONS[1], self.session)))
        self.session.run('cd ~/projects/cifar10')
        plain = self.session.run('ls')['output']
        self.assertNotIn('.env', plain)
        self.session.run('ls -a')
        self.assertTrue(all(ok for _, ok in checks(LESSONS[1], self.session)))

    def test_checkpoints_need_details_and_home(self):
        self.run_commands(['cd projects/cifar10', 'ls checkpoints'])
        self.assertFalse(all(ok for _, ok in checks(LESSONS[2], self.session)))
        self.run_commands(['ls -l -h checkpoints', 'cd', 'pwd'])
        self.assertTrue(all(ok for _, ok in checks(LESSONS[2], self.session)))

    def test_host_files_and_shell_operators_unavailable(self):
        for command in ['rm -rf /', 'ls; pwd', 'ls $(pwd)', 'ls > /tmp/output']:
            with self.assertRaises(ValueError):
                self.session.run(command)
        self.assertNotEqual(self.session.run('ls /home/yang-zhi')['exit_code'], 0)
        self.assertNotEqual(self.session.run('ls /proc/1/environ')['exit_code'], 0)
        self.assertEqual(self.session.run('pwd')['output'], '/home/student\n')

    def test_bad_cd_keeps_directory(self):
        self.assertNotEqual(self.session.run('cd /missing')['exit_code'], 0)
        self.assertEqual(self.session.cwd, '/home/student')


class ApiTests(unittest.TestCase):
    config = dict(base_url='https://example.com/v1', model='test-model')

    def call_review(self):
        return review(self.config, 'test-key', LESSONS[0], [], '我的观察', [])

    def test_valid_response_and_payload(self):
        result = dict(passed=True, feedback='合理', next_step='继续')
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = json.dumps(
            {'choices': [{'message': {'content': json.dumps(result)}}]}).encode()
        with patch('urllib.request.build_opener', return_value=opener):
            self.assertEqual(self.call_review(), result)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://example.com/v1/chat/completions')
        self.assertEqual(json.loads(request.data)['model'], 'test-model')
        self.assertNotIn('test-key', request.data.decode())

    def test_unauthorized_does_not_expose_key(self):
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect = urllib.error.HTTPError('x', 401, 'test-key', {}, None)
            with self.assertRaisesRegex(ValueError, 'HTTP 401') as error:
                self.call_review()
            self.assertNotIn('test-key', str(error.exception))

    def test_invalid_response_not_passed(self):
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.return_value.__enter__.return_value.read.return_value = b'{}'
            with self.assertRaises(ValueError):
                self.call_review()

    def test_http_rejected(self):
        with self.assertRaises(ValueError):
            review(dict(base_url='http://example.com', model='x'), 'x', {}, [], '', [])

    def test_private_state_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            save_json(path, {'passed': True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
