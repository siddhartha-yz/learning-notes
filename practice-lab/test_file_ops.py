"""Real sandbox exercises, including meaningful wrong answers. No live API calls."""
import unittest
from core import LESSONS, Session, checks

WORKFLOWS = {
    'linux-0904-workspace': [
        'pwd', 'mkdir runs/baseline/checkpoints',
        'mkdir -p runs/baseline/checkpoints runs/baseline/logs',
        'touch runs/baseline/logs/train.log', 'ls -l runs/baseline/logs',
        'cd ./runs/baseline/logs', 'cd ..', 'pwd'],
    'linux-0904-config': [
        'cat templates/baseline/config.yaml', 'cp -r templates/baseline experiment',
        'mv experiment/config.yaml experiment/train.yaml', 'cat experiment/train.yaml',
        'cd ~', 'cd ~/projects/cifar10', 'pwd'],
    'linux-0904-cleanup': [
        'more runs/review/cleanup-plan.txt', 'cd runs/review', 'ls tmp*',
        'rm tmp*', 'rm -r scratch', 'ls -l'],
}


class FileOperationTests(unittest.TestCase):
    def session(self, lesson_id):
        lesson = next(l for l in LESSONS if l['id'] == lesson_id)
        session = Session(lesson)
        self.addCleanup(session.close)
        return lesson, session

    def workflow(self, session, lesson_id):
        for command in WORKFLOWS[lesson_id]:
            record = session.run(command)
            if command == 'mkdir runs/baseline/checkpoints':
                self.assertNotEqual(record['exit_code'], 0)
            else:
                self.assertEqual(record['exit_code'], 0, record)
            while session.pager:
                session.page(' ')

    def test_all_new_lessons_can_be_completed(self):
        for lesson_id in WORKFLOWS:
            with self.subTest(lesson=lesson_id):
                lesson, session = self.session(lesson_id)
                self.assertFalse(all(ok for _, ok in checks(lesson, session)))
                self.workflow(session, lesson_id)
                self.assertTrue(all(ok for _, ok in checks(lesson, session)), checks(lesson, session))

    def test_directory_cannot_impersonate_empty_log(self):
        lesson, session = self.session('linux-0904-workspace')
        self.workflow(session, lesson['id'])
        session.run('rm logs/train.log')
        session.run('mkdir logs/train.log')
        self.assertFalse(all(ok for _, ok in checks(lesson, session)))

    def test_wrong_copy_nesting_and_missing_labels_fail(self):
        lesson, session = self.session('linux-0904-config')
        session.run('mkdir experiment')
        session.run('cp -r templates/baseline experiment')
        self.assertFalse(all(ok for _, ok in checks(lesson, session)))
        session.run('rm -r experiment')
        self.workflow(session, lesson['id'])
        session.run('rm experiment/labels.txt')
        self.assertFalse(all(ok for _, ok in checks(lesson, session)))

    def test_moving_template_instead_of_copying_fails(self):
        lesson, session = self.session('linux-0904-config')
        session.run('mv templates/baseline experiment')
        session.run('mv experiment/config.yaml experiment/train.yaml')
        self.assertFalse(all(ok for _, ok in checks(lesson, session)))

    def test_overbroad_deletion_fails_and_reset_restores_files(self):
        lesson, session = self.session('linux-0904-cleanup')
        self.workflow(session, lesson['id'])
        session.run('rm -r *')
        results = dict(checks(lesson, session))
        self.assertFalse(results['保留权重占位文件内容'])
        self.assertFalse(results['保留评估指标内容'])
        self.assertFalse(results['保留原始清理清单'])
        _, fresh = self.session(lesson['id'])
        record = fresh.run('ls runs/review')
        self.assertIn('best.pt', record['output'])
        self.assertIn('tmp_batch.cache', record['output'])

    def test_unseen_pages_are_not_submitted_as_read(self):
        lesson, session = self.session('linux-0904-cleanup')
        record = session.run('more runs/review/cleanup-plan.txt')
        self.assertNotIn('KEEP:', record['output'])
        session.page('q')
        self.assertNotIn('KEEP:', session.history[-1]['output'])
        self.assertFalse(dict(checks(lesson, session))['分页读到清单保留项'])
        session.run('more runs/review/cleanup-plan.txt')
        while session.pager:
            session.page(' ')
        self.assertIn('KEEP:', session.history[-1]['output'])

    def test_quoted_wildcard_is_literal_and_explicit_names_work(self):
        lesson, session = self.session('linux-0904-cleanup')
        session.run('cd runs/review')
        self.assertNotEqual(session.run("ls 'tmp*'")['exit_code'], 0)
        self.assertEqual(session.run('ls tmp*')['exit_code'], 0)
        self.assertEqual(session.run('rm tmp_batch.cache tmp_worker.log')['exit_code'], 0)
        self.assertIn('best.pt', session.run('ls')['output'])

    def test_writes_are_isolated_from_host_and_readonly_data(self):
        _, session = self.session('linux-0904-workspace')
        self.assertNotEqual(session.run('touch /datasets/cifar10/probe')['exit_code'], 0)
        self.assertNotEqual(session.run('touch /home/yang-zhi/probe')['exit_code'], 0)
        self.assertNotEqual(session.run('rm /usr/bin/cat')['exit_code'], 0)
        for command in ['touch x; pwd', 'cp $(pwd) x', 'touch x\npwd']:
            with self.assertRaises(ValueError):
                session.run(command)

    def test_state_checker_does_not_follow_host_symlinks(self):
        lesson, session = self.session('linux-0904-config')
        session.run('mkdir experiment')
        session.run('cp -s /etc/passwd experiment/train.yaml')
        self.assertFalse(dict(checks(lesson, session))['重命名后的配置内容与模板一致'])


if __name__ == '__main__':
    unittest.main()
