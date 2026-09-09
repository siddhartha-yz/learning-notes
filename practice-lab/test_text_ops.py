"""September 6: real find, pipes, redirection; no student data or live API."""
import unittest
from core import LESSONS, Session, checks

WORKFLOWS = {
 'linux-0906-find': ['which python3', 'find artifacts -name "*.pt"', 'find artifacts -name "*.pt" -size +100M'],
 'linux-0906-errors': ['cat train.log', 'grep -n "ERROR" train.log', 'grep "ERROR" train.log | wc -l'],
 'linux-0906-report': ['cat metrics.log', 'grep "split=val" metrics.log > summary.txt',
                       'echo "project=`pwd`" >> summary.txt', 'echo "status=reviewed" >> summary.txt', 'tail -3 summary.txt'],
}

class TextTests(unittest.TestCase):
    def session(self, name):
        lesson = next(l for l in LESSONS if l['id'] == name)
        s = Session(lesson)
        self.addCleanup(s.close)
        return lesson, s

    def test_all_workflows(self):
        for name, commands in WORKFLOWS.items():
            with self.subTest(name=name):
                lesson, s = self.session(name)
                self.assertFalse(all(ok for _, ok in checks(lesson, s)))
                for command in commands:
                    r = s.run(command)
                    self.assertEqual(r['exit_code'], 0, r)
                self.assertTrue(all(ok for _, ok in checks(lesson, s)), checks(lesson, s))

    def test_find_accepts_equivalent_relative_paths(self):
        lesson, s = self.session('linux-0906-find')
        for c in ['which python3', 'cd artifacts', 'find . -name "*.pt"', 'find . -size +100M -name "*.pt"']:
            self.assertEqual(s.run(c)['exit_code'], 0)
        self.assertTrue(all(ok for _, ok in checks(lesson, s)), checks(lesson, s))

    def test_find_size_without_name_includes_wrong_artifact(self):
        lesson, s = self.session('linux-0906-find')
        r = s.run('find artifacts -size +100M')
        self.assertIn('debug.log', r['output'])
        self.assertFalse(dict(checks(lesson, s))['只筛出两个大于 100 MiB 的权重文件'])

    def test_whole_log_count_is_not_error_count(self):
        lesson, s = self.session('linux-0906-errors')
        self.assertEqual(s.run('cat train.log | wc -l')['output'].strip(), '6')
        self.assertFalse(dict(checks(lesson, s))['通过筛选管道统计出 2 条错误记录'])
        self.assertEqual(s.run('cat train.log | grep ERROR | wc -l')['output'].strip(), '2')
        self.assertTrue(dict(checks(lesson, s))['通过筛选管道统计出 2 条错误记录'])

    def test_pipeline_reports_upstream_failure(self):
        _, s = self.session('linux-0906-errors')
        self.assertNotEqual(s.run('grep ERROR missing.log | wc -l')['exit_code'], 0)

    def test_append_keeps_stale_and_overwrite_loses_records(self):
        lesson, s = self.session('linux-0906-report')
        s.run('grep split=val metrics.log >> summary.txt')
        self.assertIn('STALE', s.run('cat summary.txt')['output'])
        self.assertFalse(dict(checks(lesson, s))['摘要含完整验证记录与追加说明'])
        for c in WORKFLOWS[lesson['id']]: s.run(c)
        s.run('echo status=reviewed > summary.txt')
        self.assertFalse(dict(checks(lesson, s))['摘要含完整验证记录与追加说明'])

    def test_raw_metrics_modification_fails(self):
        lesson, s = self.session('linux-0906-report')
        s.run('echo changed > metrics.log')
        self.assertFalse(dict(checks(lesson, s))['原始指标保持不变'])

    def test_pipeline_and_substitution_are_scoped(self):
        _, s = self.session('linux-0906-report')
        for c in ['echo x | bash', 'echo `ls`', 'echo $(pwd)', 'echo x; pwd',
                  'find . -exec cat /etc/passwd \\;', 'echo x | find . -delete',
                  'echo x || pwd', 'tail -f metrics.log', 'echo x >']:
            with self.subTest(c=c), self.assertRaises(ValueError): s.run(c)
        self.assertNotEqual(s.run('echo x > /datasets/cifar10/probe')['exit_code'], 0)
        self.assertNotEqual(s.run('echo x > /home/yang-zhi/probe')['exit_code'], 0)

if __name__ == '__main__': unittest.main()
