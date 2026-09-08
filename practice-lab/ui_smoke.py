"""Run inside a Linux desktop: python3 practice-lab/ui_smoke.py.
Uses temporary progress/logs and a mock reviewer; does not call a model service.
"""
from pathlib import Path
import tempfile
import time
from unittest.mock import patch
import app
import core
from test_file_ops import WORKFLOWS
from gi.repository import Gtk, Gdk


def settle(window):
    deadline = time.monotonic() + 10
    while window.busy:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if time.monotonic() > deadline:
            raise AssertionError('UI operation timed out')
        time.sleep(0.01)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


def main():
    Gtk.Settings.get_default().set_property('gtk-enable-animations', False)
    with tempfile.TemporaryDirectory() as temporary, \
         patch.object(app, 'STATE', Path(temporary) / 'state'), \
         patch.object(core, 'ATTEMPTS', Path(temporary) / 'attempts'), \
         patch.object(app, 'review', return_value=dict(passed=True, feedback='本题回答正确，已通过。', next_step='')):
        window = app.Lab()
        window.show_all()
        try:
            window.config = dict(base_url='https://example.com/v1', model='mock')
            window.key = 'mock'
            # Preserve existing chapter semantics when a second chapter is added.
            for lesson in app.LESSONS[:3]:
                window.progress[lesson['id']] = {'passed': True}
            window.selector.set_active(2)
            assert '26.9.3 本组完成' in window.lesson_status.get_text()
            assert '26.9.4' in window.next_button.get_label()
            window.next_button.emit('clicked')
            for index, lesson in enumerate(app.LESSONS[3:], 3):
                assert window.index == index
                assert '26.9.4' in window.subtitle.get_text()
                assert window.session.writable
                for command in WORKFLOWS[lesson['id']]:
                    window.entry.set_text(command)
                    window.entry.emit('activate')
                    settle(window)
                    while window.session.pager:
                        event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
                        event.keyval = Gdk.KEY_space
                        window.entry.emit('key-press-event', event)
                assert all(ok for _, ok in core.checks(lesson, window.session))
                window.answer.get_buffer().set_text('自动界面测试占位答案；模型评审为模拟，不是学生作答。')
                window.submit.emit('clicked')
                settle(window)
                assert window.progress[lesson['id']]['passed']
                if index < len(app.LESSONS) - 1:
                    assert window.next_button.get_visible()
                    window.next_button.emit('clicked')
                    assert not window.session.history
            assert '全部完成' in window.lesson_status.get_text()
            assert not window.next_button.get_visible()
            logs = list(core.ATTEMPTS.rglob('*.json'))
            assert len(logs) == 3
            for path in logs:
                data = core.read_json(path, {})
                assert data['status'] == 'reviewed'
                assert data['lesson']['chapter'] == '26.9.4'
                assert data['history'] and data['local_checks']
            window.selector.set_active(0)
            assert not window.session.writable
            assert len(window.session.commands) == 3
            print('GTK smoke passed: chapter navigation, 3 real workflows, Space paging, mock review, logs, completion, old chapter')
        finally:
            window.session.close()
            window.destroy()


if __name__ == '__main__':
    main()
