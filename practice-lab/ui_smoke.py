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
from gi.repository import Gtk, Gdk, GLib


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
            assert len(window.selector.get_model()) == 3
            assert len(window.chapter_selector.get_model()) == 2
            window.chapter_selector.set_active(1)
            assert window.index == 3
            assert len(window.selector.get_model()) == 3
            assert '26.9.3' not in window.selector.get_active_text()
            # Exercise the actual settings dialog, then reopen the app from saved state.
            def save_dialog():
                dialog = next(w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog))
                fields = [w for w in dialog.get_content_area().get_children() if isinstance(w, Gtk.Entry)]
                for field, value in zip(fields, ['https://example.com/v1', 'mock', 'synthetic-ui-secret']):
                    field.set_text(value)
                dialog.response(Gtk.ResponseType.OK)
                return False
            GLib.timeout_add(20, save_dialog)
            window.settings()
            assert core.load_api_key(app.STATE, window.config) == 'synthetic-ui-secret'
            with patch.dict('os.environ', {'LEARNING_LAB_API_KEY': ''}):
                reopened = app.Lab()
            assert reopened.key == 'synthetic-ui-secret'
            reopened.session.close()
            reopened.destroy()
            # Preserve existing chapter semantics when a second chapter is added.
            for lesson in app.LESSONS[:3]:
                window.progress[lesson['id']] = {'passed': True}
            window.select_lesson(2)
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
            window.select_lesson(0)
            assert not window.session.writable
            assert len(window.session.commands) == 3
            print('GTK smoke passed: chapter navigation, 3 real workflows, Space paging, mock review, logs, completion, old chapter')
        finally:
            window.session.close()
            window.destroy()


if __name__ == '__main__':
    main()
