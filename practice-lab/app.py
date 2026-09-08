#!/usr/bin/env python3
"""Native GTK desktop app; start with ./launch.sh."""
import os
from pathlib import Path
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from core import LESSONS, STATE, Session, checks, read_json, save_json, review


class Lab(Gtk.Window):
    def __init__(self):
        super().__init__(title='Learning Notes · 实践工坊')
        self.set_default_size(1120, 800)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.session = Session()
        self.index = 0
        self.busy = False
        self.config = read_json(STATE / 'api.json', {})
        self.key = os.environ.get('LEARNING_LAB_API_KEY', '')
        self.progress = read_json(STATE / 'progress.json', {})
        self.connect('delete-event', self.close)
        css = Gtk.CssProvider()
        css.load_from_data(b'''
            window { background: #f5f3ed; color: #253831; }
            button { padding: 8px 14px; border-radius: 7px; background: #e5eae4; color: #253831; }
            textview text, entry { background: #ffffff; color: #253831; }
            .title { font-size: 25px; font-weight: bold; }
            .subtitle { color: #60746c; }
            .passed { background: #dcefe2; color: #195b35; padding: 10px; font-weight: bold; }
            .terminal text { background: #182c28; color: #d5e8d9; }
            .terminal { font-family: monospace; font-size: 14px; }
            .primary { background: #286b54; color: white; }
            entry { padding: 9px; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20)
        self.add(root)
        top = Gtk.Box(spacing=12)
        title = Gtk.Label(label='实践工坊', xalign=0)
        title.get_style_context().add_class('title')
        top.pack_start(title, True, True, 0)
        settings = Gtk.Button(label='API 设置')
        settings.connect('clicked', self.settings)
        top.pack_start(settings, False, False, 0)
        root.pack_start(top, False, False, 0)
        subtitle = Gtk.Label(label='LINUX  /  26.9.3     从笔记到一次真实操作 · CIFAR-10 训练准备', xalign=0)
        subtitle.get_style_context().add_class('subtitle')
        root.pack_start(subtitle, False, False, 0)
        self.selector = Gtk.ComboBoxText()
        for lesson in LESSONS:
            self.selector.append_text(lesson['title'])
        self.selector.set_active(0)
        self.selector.connect('changed', self.select)
        root.pack_start(self.selector, False, False, 0)
        status_row = Gtk.Box(spacing=12)
        self.lesson_status = Gtk.Label(xalign=0, wrap=True)
        status_row.pack_start(self.lesson_status, True, True, 0)
        self.next_button = Gtk.Button(label='进入下一题 →')
        self.next_button.get_style_context().add_class('primary')
        self.next_button.set_no_show_all(True)
        self.next_button.connect('clicked', self.advance)
        status_row.pack_start(self.next_button, False, False, 0)
        root.pack_start(status_row, False, False, 0)
        pane = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(pane, True, True, 0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_end=16)
        left.set_size_request(380, -1)
        pane.pack1(left, False, False)
        self.task = Gtk.Label(xalign=0, yalign=0, wrap=True, selectable=True)
        self.task.set_max_width_chars(42)
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        task_scroll.add(self.task)
        left.pack_start(task_scroll, True, True, 0)
        hint = Gtk.Button(label='给我一点提示')
        hint.connect('clicked', lambda _: self.message(LESSONS[self.index]['hint']))
        left.pack_start(hint, False, False, 0)
        source = Gtk.Button(label='阅读对应笔记')
        source.connect('clicked', self.source)
        left.pack_start(source, False, False, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        pane.pack2(right, True, False)
        self.terminal = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.terminal.set_left_margin(12)
        self.terminal.set_top_margin(12)
        self.terminal.get_style_context().add_class('terminal')
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(240)
        scroll.add(self.terminal)
        right.pack_start(scroll, True, True, 0)
        self.location = Gtk.Label(xalign=0)
        right.pack_start(self.location, False, False, 0)
        self.entry = Gtk.Entry(placeholder_text='输入 ls、cd 或 pwd，按 Enter 执行')
        self.entry.connect('activate', self.run)
        right.pack_start(self.entry, False, False, 0)
        right.pack_start(Gtk.Label(label='观察与解释  ·  提交你从输出中得到的证据', xalign=0), False, False, 0)
        self.answer = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.answer.set_left_margin(8)
        self.answer.set_top_margin(8)
        answer_scroll = Gtk.ScrolledWindow()
        answer_scroll.set_min_content_height(100)
        answer_scroll.add(self.answer)
        right.pack_start(answer_scroll, False, False, 0)
        actions = Gtk.Box(spacing=8)
        self.submit = Gtk.Button(label='提交给 Agent 检验')
        self.submit.get_style_context().add_class('primary')
        self.submit.connect('clicked', self.evaluate)
        self.reset = Gtk.Button(label='重置本题')
        self.reset.connect('clicked', self.restart)
        actions.pack_start(self.submit, True, True, 0)
        actions.pack_start(self.reset, False, False, 0)
        right.pack_start(actions, False, False, 0)
        self.feedback = Gtk.Label(xalign=0, yalign=0, wrap=True, selectable=True)
        self.feedback.set_max_width_chars(100)
        feedback_scroll = Gtk.ScrolledWindow()
        feedback_scroll.set_min_content_height(110)
        feedback_scroll.add(self.feedback)
        root.pack_start(feedback_scroll, False, False, 0)
        self.load()

    def message(self, text):
        self.feedback.set_text(text)

    def append(self, text):
        buffer = self.terminal.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.terminal.scroll_to_mark(mark, 0, False, 0, 0)
        buffer.delete_mark(mark)

    def load(self):
        lesson = LESSONS[self.index]
        completed = sum(v.get('passed', False) for v in self.progress.values())
        self.task.set_text(lesson['title'] + '\n\n' + lesson['brief'] + '\n\n你的任务\n\n' + lesson['steps'])
        self.terminal.get_buffer().set_text('练习终端 · 真实 Linux 命令\n本课支持 ls / cd / pwd，一次一条；保留当前目录。\n临时数据只读，与个人文件及网络隔离。\n\n')
        self.answer.get_buffer().set_text('')
        self.location.set_text(self.session.cwd + '  $')
        self.message(f'已完成 {completed} / {len(LESSONS)} 题。操作后写下观察，再提交评审。')
        self.update_completion()

    def update_completion(self):
        completed = sum(bool(self.progress.get(item['id'], {}).get('passed')) for item in LESSONS)
        passed = self.progress.get(LESSONS[self.index]['id'], {}).get('passed', False)
        style = self.lesson_status.get_style_context()
        style.remove_class('passed')
        if completed == len(LESSONS):
            text = f'✓ 全部完成！{completed} / {len(LESSONS)} 题已通过，可自由选题复习。'
            style.add_class('passed')
        elif passed:
            text = f'✓ 本题已通过 · 已完成 {completed} / {len(LESSONS)} 题'
            style.add_class('passed')
        else:
            text = f'第 {self.index + 1} / {len(LESSONS)} 题 · 待通过 · 已完成 {completed} 题'
        self.lesson_status.set_text(text)
        model = self.selector.get_model()
        for index, item in enumerate(LESSONS):
            mark = '✓ 已通过  ' if self.progress.get(item['id'], {}).get('passed') else ''
            model[index][0] = mark + item['title']
        self.next_button.set_label('进入下一题 →' if self.index < len(LESSONS) - 1 else '继续未完成的题目 →')
        self.next_button.set_visible(bool(passed) and completed < len(LESSONS))

    def advance(self, *_):
        if self.busy or not self.progress.get(LESSONS[self.index]['id'], {}).get('passed'):
            return
        if self.index < len(LESSONS) - 1:
            self.selector.set_active(self.index + 1)
        else:
            for index, lesson in enumerate(LESSONS):
                if not self.progress.get(lesson['id'], {}).get('passed'):
                    self.selector.set_active(index)
                    break
        self.entry.grab_focus()

    def select(self, widget):
        self.index = widget.get_active()
        self.restart()

    def restart(self, *_):
        if self.busy:
            return
        self.session.close()
        self.session = Session()
        self.load()

    def set_busy(self, value):
        self.busy = value
        for widget in [self.selector, self.entry, self.submit, self.reset, self.answer, self.next_button]:
            widget.set_sensitive(not value)

    def background(self, action, done):
        self.set_busy(True)
        def worker():
            try:
                result, error = action(), None
            except Exception as exc:
                result, error = None, str(exc)
            GLib.idle_add(finish, result, error)
        def finish(result, error):
            self.set_busy(False)
            if error:
                self.message(error.replace(self.key, '[密钥已隐藏]') if self.key else error)
            else:
                done(result)
            return False
        threading.Thread(target=worker, daemon=True).start()

    def run(self, entry):
        command = entry.get_text().strip()
        if not command or self.busy:
            return
        self.append(self.session.cwd + ' $ ' + command + '\n')
        entry.set_text('')
        def done(record):
            self.append(record['output'] + '\n' + (f"[退出码 {record['exit_code']}]\n" if record['exit_code'] else ''))
            self.location.set_text(self.session.cwd + '  $')
            self.entry.grab_focus()
        self.background(lambda: self.session.run(command), done)

    def evaluate(self, *_):
        buffer = self.answer.get_buffer()
        answer = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        lesson = LESSONS[self.index]
        local = checks(lesson, self.session)
        summary = '\n'.join(('✓ ' if ok else '○ ') + name for name, ok in local)
        if not answer:
            self.message(summary + '\n请先写下观察与解释。')
            return
        if len(answer) > 6000:
            self.message('请把观察与解释控制在 6000 字以内。')
            return
        if not self.key or not self.config.get('base_url') or not self.config.get('model'):
            self.message(summary + '\n未完成 Agent 评审：请先配置 API 地址、模型名和密钥。')
            return
        self.message(summary + '\nAgent 正在阅读本题命令记录与解释…')
        config, key, history = dict(self.config), self.key, list(self.session.history)
        def done(result):
            passed = all(ok for _, ok in local) and result['passed']
            self.progress[lesson['id']] = {'passed': passed, 'feedback': result['feedback']}
            save_json(STATE / 'progress.json', self.progress)
            self.update_completion()
            self.message(summary + '\n\n' + ('通过！' if passed else '继续尝试：') + result['feedback'] + '\n' + result['next_step'])
        self.background(lambda: review(config, key, lesson, history, answer, local), done)

    def settings(self, *_):
        dialog = Gtk.Dialog(title='模型 API 设置', transient_for=self, modal=True)
        dialog.add_buttons('取消', Gtk.ResponseType.CANCEL, '保存', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_border_width(18)
        fields = []
        for label, value, hidden in [('Base URL（包含 /v1 等服务商前缀，不含 /chat/completions）', self.config.get('base_url', ''), False),
                                      ('模型名', self.config.get('model', ''), False), ('API 密钥（仅当前运行期间保存）', self.key, True)]:
            box.pack_start(Gtk.Label(label=label, xalign=0), False, False, 0)
            entry = Gtk.Entry(text=value, visibility=not hidden)
            entry.set_width_chars(62)
            box.pack_start(entry, False, False, 0)
            fields.append(entry)
        note = Gtk.Label(label='提交时仅向此服务发送本题题目、命令输出和你的解释。\n地址和模型保存在本机；密钥不写入仓库或配置文件。', xalign=0)
        box.pack_start(note, False, False, 0)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.config = dict(base_url=fields[0].get_text().strip(), model=fields[1].get_text().strip())
            self.key = fields[2].get_text().strip()
            save_json(STATE / 'api.json', self.config)
            self.message('API 设置已保存。填写观察后可提交给 Agent。')
        dialog.destroy()

    def source(self, *_):
        path = Path(__file__).resolve().parent.parent / LESSONS[self.index]['source']
        dialog = Gtk.Dialog(title='原始笔记 · 26.9.3', transient_for=self)
        dialog.set_default_size(700, 650)
        dialog.add_button('关闭', Gtk.ResponseType.CLOSE)
        view = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(path.read_text())
        scroll = Gtk.ScrolledWindow()
        scroll.add(view)
        dialog.get_content_area().pack_start(scroll, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def close(self, *_):
        if self.busy:
            self.message('正在执行或评审，请等待本次操作结束后关闭（API 最长约 45 秒）。')
            return True
        self.session.close()
        Gtk.main_quit()
        return False


if __name__ == '__main__':
    window = Lab()
    window.show_all()
    Gtk.main()
