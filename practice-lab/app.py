#!/usr/bin/env python3
"""Native GTK desktop app; start with ./launch.sh."""
import os
from pathlib import Path
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from core import LESSONS, STATE, Session, checks, read_json, save_json, review, start_attempt, finish_attempt, review_message, load_api_key, save_api_settings


from torch_panel import TorchPanel


class Lab(Gtk.Window):
    def __init__(self):
        super().__init__(title='Learning Notes · 实践工坊')
        self.set_default_size(1120, 800)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.session = Session()
        self.index = 0
        self.busy = False
        self.config = read_json(STATE / 'api.json', {})
        self.key = os.environ.get('LEARNING_LAB_API_KEY') or load_api_key(STATE, self.config)
        self.progress = read_json(STATE / 'progress.json', {})
        self.connect('delete-event', self.close)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name('night.css')))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=20)
        self.add(root)
        top = Gtk.Box(spacing=12)
        title = Gtk.Label(label='>_ 实践工坊', xalign=0)
        title.get_style_context().add_class('title')
        top.pack_start(title, True, True, 0)
        settings = Gtk.Button(label='API 设置')
        settings.connect('clicked', self.settings)
        top.pack_start(settings, False, False, 0)
        root.pack_start(top, False, False, 0)
        self.subtitle = Gtk.Label(xalign=0)
        self.subtitle.get_style_context().add_class('subtitle')
        root.pack_start(self.subtitle, False, False, 0)
        self.tracks = list(dict.fromkeys(item['track'] for item in LESSONS))
        self.track_selector = Gtk.ComboBoxText()
        for track in self.tracks:
            self.track_selector.append_text(track + (' · 命令实践' if track == 'Linux' else ' · 模型的可执行表示'))
        self.track_selector.set_active(0)
        self.track_selector.connect('changed', self.select_track)
        root.pack_start(self.track_selector, False, False, 0)
        self.chapters = list(dict.fromkeys(item['chapter'] for item in LESSONS if item['track'] == 'Linux'))
        self.chapter_indices = []
        self.selecting = False
        navigation = Gtk.Box(spacing=12)
        chapter_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label='CHAPTER / 笔记日期', xalign=0)
        self.chapter_caption = label
        label.get_style_context().add_class('section-label')
        chapter_box.pack_start(label, False, False, 0)
        self.chapter_selector = Gtk.ComboBoxText()
        for chapter in self.chapters:
            count = sum(item['chapter'] == chapter for item in LESSONS)
            self.chapter_selector.append_text(f'{chapter}   ·   {count} 道题')
        self.chapter_selector.set_active(0)
        self.chapter_selector.connect('changed', self.select_chapter)
        chapter_box.pack_start(self.chapter_selector, False, False, 0)
        navigation.pack_start(chapter_box, False, False, 0)
        lesson_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label='EXERCISE / 本章题目', xalign=0)
        label.get_style_context().add_class('section-label')
        lesson_box.pack_start(label, False, False, 0)
        self.selector = Gtk.ComboBoxText()
        self.selector.connect('changed', self.select)
        lesson_box.pack_start(self.selector, False, False, 0)
        navigation.pack_start(lesson_box, True, True, 0)
        root.pack_start(navigation, False, False, 0)
        self.populate_lessons(0)
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
        left.set_size_request(400, -1)
        left.get_style_context().add_class('task-panel')
        pane.pack1(left, False, False)
        self.task = Gtk.Label(xalign=0, yalign=0, wrap=True, selectable=True)
        self.task.set_max_width_chars(42)
        self.task.get_style_context().add_class('task-copy')
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        task_scroll.set_overlay_scrolling(False)
        task_scroll.add(self.task)
        left.pack_start(task_scroll, True, True, 0)
        hint = Gtk.Button(label='给我一点提示')
        hint.connect('clicked', self.hint)
        left.pack_start(hint, False, False, 0)
        source = Gtk.Button(label='阅读对应笔记')
        self.source_button = source
        source.connect('clicked', self.source)
        left.pack_start(source, False, False, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.content_stack = Gtk.Stack()
        self.content_stack.add_named(right, 'linux')
        self.torch_panel = TorchPanel(self, STATE)
        self.content_stack.add_named(self.torch_panel, 'pytorch')
        pane.pack2(self.content_stack, True, False)
        self.terminal = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.terminal.set_left_margin(12)
        self.terminal.set_top_margin(12)
        self.terminal.get_style_context().add_class('terminal')
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(240)
        scroll.add(self.terminal)
        right.pack_start(scroll, True, True, 0)
        self.location = Gtk.Label(xalign=0)
        self.location.get_style_context().add_class('prompt')
        right.pack_start(self.location, False, False, 0)
        self.entry = Gtk.Entry(placeholder_text='输入 ls、cd 或 pwd，按 Enter 执行')
        self.entry.connect('activate', self.run)
        self.entry.connect('key-press-event', self.pager_key)
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
        self.chapter_caption.set_text('CHAPTER / 能力阶段' if lesson['track'] == 'PyTorch' else 'CHAPTER / 笔记日期')
        self.source_button.set_label('阅读路线与关联笔记' if lesson['track'] == 'PyTorch' else '阅读对应笔记')
        group = [item for item in LESSONS if item['chapter'] == lesson['chapter']]
        completed = sum(bool(self.progress.get(item['id'], {}).get('passed')) for item in group)
        self.subtitle.set_text(lesson['track'].upper() + '  /  ' + lesson['chapter'] + ('     预测 → 实现 → 验证 → 解释' if lesson['track'] == 'PyTorch' else '     从笔记到真实操作 · CIFAR-10 实验实践'))
        self.task.set_text(lesson['title'] + '\n\n' + lesson['brief'] + '\n\n你的任务\n\n' + lesson['steps'])
        access = '临时 Home 可读写；原始数据只读' if self.session.writable else '临时数据只读'
        self.terminal.get_buffer().set_text('练习终端 · 真实 Linux 命令\n支持 ' + ' / '.join(self.session.commands) + '\n' + access + '，与个人文件及网络隔离。\n\n')
        self.entry.set_text('')
        self.update_prompt()
        self.answer.get_buffer().set_text('')
        self.location.set_text(self.session.cwd + '  $')
        self.message(f'本章已完成 {completed} / {len(group)} 题。操作后写下观察，再提交评审。')
        self.content_stack.set_visible_child_name('pytorch' if lesson['track'] == 'PyTorch' else 'linux')
        if lesson['track'] == 'PyTorch':
            self.torch_panel.load(lesson)
        self.update_completion()

    def hint(self, *_):
        if LESSONS[self.index]['track'] == 'PyTorch':
            self.torch_panel.hint()
        else:
            self.message(LESSONS[self.index]['hint'])

    def select_track(self, widget):
        if self.selecting or self.busy or widget.get_active() < 0:
            return
        track = self.tracks[widget.get_active()]
        self.select_lesson(next(i for i, lesson in enumerate(LESSONS) if lesson['track'] == track))

    def populate_lessons(self, index):
        self.selecting = True
        chapter = LESSONS[index]['chapter']
        track = LESSONS[index]['track']
        self.track_selector.set_active(self.tracks.index(track))
        self.chapters = list(dict.fromkeys(item['chapter'] for item in LESSONS if item['track'] == track))
        self.chapter_selector.remove_all()
        for name in self.chapters:
            count = sum(item['chapter'] == name for item in LESSONS)
            self.chapter_selector.append_text(f'{name}   ·   {count} 道题')
        self.chapter_indices = [i for i, item in enumerate(LESSONS) if item['chapter'] == chapter]
        self.chapter_selector.set_active(self.chapters.index(chapter))
        self.selector.remove_all()
        for i in self.chapter_indices:
            self.selector.append_text(LESSONS[i]['title'])
        self.selector.set_active(self.chapter_indices.index(index))
        self.selecting = False

    def select_lesson(self, index):
        if self.busy:
            return
        self.index = index
        self.populate_lessons(index)
        self.restart()

    def select_chapter(self, widget):
        if self.selecting or self.busy or widget.get_active() < 0:
            return
        chapter = self.chapters[widget.get_active()]
        indices = [i for i, item in enumerate(LESSONS) if item['chapter'] == chapter]
        target = next((i for i in indices if not self.progress.get(LESSONS[i]['id'], {}).get('passed')), indices[0])
        self.select_lesson(target)

    def update_completion(self):
        passed = bool(self.progress.get(LESSONS[self.index]['id'], {}).get('passed'))
        chapter = LESSONS[self.index]['chapter']
        indices = self.chapter_indices
        completed = sum(bool(self.progress.get(LESSONS[i]['id'], {}).get('passed')) for i in indices)
        track = LESSONS[self.index]['track']
        track_lessons = [(i, item) for i, item in enumerate(LESSONS) if item['track'] == track]
        all_done = all(self.progress.get(item['id'], {}).get('passed') for _, item in track_lessons)
        style = self.lesson_status.get_style_context()
        style.remove_class('passed')
        if all_done:
            text = f'✓ 全部完成！ · {chapter} 本章 {completed} / {len(indices)} 题已通过'
        elif completed == len(indices):
            text = f'✓ {chapter} 本组完成！{completed} / {len(indices)} 题已通过'
        elif passed:
            text = f'✓ 本题已通过 · 本章已完成 {completed} / {len(indices)} 题'
        else:
            text = f'{chapter}  /  第 {indices.index(self.index) + 1} 题，共 {len(indices)} 题 · 待通过'
        if passed:
            style.add_class('passed')
        self.lesson_status.set_text(text)
        model = self.selector.get_model()
        for row, i in enumerate(indices):
            mark = '✓ 已通过  ' if self.progress.get(LESSONS[i]['id'], {}).get('passed') else ''
            model[row][0] = mark + LESSONS[i]['title']
        self.next_index = None
        if passed and not all_done:
            position = indices.index(self.index)
            if position + 1 < len(indices):
                self.next_index = indices[position + 1]
            else:
                self.next_index = next((i for i in indices if not self.progress.get(LESSONS[i]['id'], {}).get('passed')), None)
                if self.next_index is None:
                    self.next_index = next(i for i, item in track_lessons if not self.progress.get(item['id'], {}).get('passed'))
        label = '进入下一题 →'
        if self.next_index is not None and LESSONS[self.next_index]['chapter'] != chapter:
            label = '进入 ' + LESSONS[self.next_index]['chapter'] + ' 练习 →'
        self.next_button.set_label(label)
        self.next_button.set_visible(self.next_index is not None)

    def advance(self, *_):
        if not self.busy and self.next_index is not None:
            self.select_lesson(self.next_index)
            self.entry.grab_focus()

    def select(self, widget):
        if not self.selecting and not self.busy and widget.get_active() >= 0:
            self.index = self.chapter_indices[widget.get_active()]
            self.restart()

    def restart(self, *_):
        if self.busy:
            return
        self.session.close()
        self.session = Session(LESSONS[self.index])
        self.load()

    def set_busy(self, value):
        self.busy = value
        for widget in [self.track_selector, self.chapter_selector, self.selector, self.entry, self.submit, self.reset, self.answer, self.next_button]:
            widget.set_sensitive(not value)
        self.torch_panel.set_busy(value)

    def background(self, action, done, on_error=None):
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
                if on_error:
                    on_error()
                self.message(error.replace(self.key, '[密钥已隐藏]') if self.key else error)
            else:
                done(result)
            return False
        threading.Thread(target=worker, daemon=True).start()

    def update_prompt(self):
        self.entry.set_placeholder_text('Space 下一页 · q 退出分页' if self.session.pager else '输入本课命令，按 Enter 执行')
        self.location.set_text('— more · Space 下一页 / q 退出 —' if self.session.pager else self.session.cwd + '  $')

    def pager_key(self, entry, event):
        if self.session.pager and not self.busy:
            key = Gdk.keyval_name(event.keyval)
            if key in ('space', 'q'):
                self.append(self.session.page('q' if key == 'q' else ' '))
                if not self.session.pager:
                    self.append('[分页结束]\n')
                self.update_prompt()
            return True
        return False

    def run(self, entry):
        command = entry.get_text().strip()
        if not command or self.busy:
            return
        self.append(self.session.cwd + ' $ ' + command + '\n')
        entry.set_text('')
        def done(record):
            self.append(record['output'] + '\n' + (f"[退出码 {record['exit_code']}]\n" if record['exit_code'] else ''))
            self.update_prompt()
            self.entry.grab_focus()
        self.background(lambda: self.session.run(command), done)

    def evaluate(self, *_):
        buffer = self.answer.get_buffer()
        answer = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False).strip()
        lesson = LESSONS[self.index]
        if self.session.pager:
            self.message('请先读完分页内容或按 q 退出，再提交答案。')
            return
        local = checks(lesson, self.session)
        summary = '\n'.join(('✓ ' if ok else '○ ') + name for name, ok in local)
        if not answer:
            self.message(summary + '\n请先写下观察与解释。')
            return
        if len(answer) > 6000:
            self.message('请把观察与解释控制在 6000 字以内。')
            return
        try:
            attempt = start_attempt(lesson, list(self.session.history), answer, local, self.key)
        except OSError:
            self.message('答题日志保存失败，请检查仓库写入权限后重试。')
            return
        if not self.key or not self.config.get('base_url') or not self.config.get('model'):
            finish_attempt(attempt, 'api_not_configured')
            self.message(summary + '\n未完成 Agent 评审：请先配置 API 地址、模型名和密钥。')
            return
        self.message(summary + '\nAgent 正在阅读本题命令记录与解释…')
        config, key, history = dict(self.config), self.key, list(self.session.history)
        def done(result):
            passed = all(ok for _, ok in local) and result['passed']
            finish_attempt(attempt, 'reviewed', result, passed)
            self.progress[lesson['id']] = {'passed': passed, 'feedback': result['feedback']}
            save_json(STATE / 'progress.json', self.progress)
            self.update_completion()
            self.message(summary + '\n\n' + review_message(passed, result))
        self.background(lambda: review(config, key, lesson, history, answer, local), done,
                        on_error=lambda: finish_attempt(attempt, 'api_error'))

    def settings(self, *_):
        dialog = Gtk.Dialog(title='模型 API 设置', transient_for=self, modal=True)
        dialog.add_buttons('取消', Gtk.ResponseType.CANCEL, '保存', Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_border_width(18)
        fields = []
        for label, value, hidden in [('Base URL（包含 /v1 等服务商前缀，不含 /chat/completions）', self.config.get('base_url', ''), False),
                                      ('模型名', self.config.get('model', ''), False), ('API 密钥', self.key, True)]:
            box.pack_start(Gtk.Label(label=label, xalign=0), False, False, 0)
            entry = Gtk.Entry(text=value, visibility=not hidden)
            entry.set_width_chars(62)
            box.pack_start(entry, False, False, 0)
            fields.append(entry)
        remember = Gtk.CheckButton(label='在本机记住密钥，下次启动自动加载')
        remember.set_active(self.config.get('remember_key', True))
        box.pack_start(remember, False, False, 0)
        note = Gtk.Label(label='密钥保存在仓库外、仅当前用户可读写的本机文件中。\n取消勾选并保存会删除已保存的密钥；留空保存也可清除。', xalign=0)
        box.pack_start(note, False, False, 0)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            self.config = dict(base_url=fields[0].get_text().strip(), model=fields[1].get_text().strip(), remember_key=remember.get_active())
            self.key = fields[2].get_text().strip()
            try:
                save_api_settings(STATE, self.config, self.key, remember.get_active())
                self.message('API 设置已保存。' + ('下次启动将自动加载密钥。' if remember.get_active() and self.key else '密钥仅用于本次运行。'))
            except OSError:
                self.message('本机设置保存失败，请检查状态目录权限。当前密钥仍可在本次运行中使用。')
        dialog.destroy()

    def source(self, *_):
        lesson = LESSONS[self.index]
        paths = [lesson['source']] + lesson.get('sources', [])
        dialog = Gtk.Dialog(title='学习资料 · ' + lesson['chapter'], transient_for=self)
        dialog.set_default_size(760, 650)
        dialog.add_button('关闭', Gtk.ResponseType.CLOSE)
        view = Gtk.TextView(editable=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        def show_source(index):
            path = Path(__file__).resolve().parent.parent / paths[index]
            view.get_buffer().set_text(path.read_text())
        if len(paths) > 1:
            choices = Gtk.ComboBoxText()
            for path in paths:
                choices.append_text(path)
            choices.set_active(0)
            choices.connect('changed', lambda widget: show_source(widget.get_active()))
            dialog.get_content_area().pack_start(choices, False, False, 0)
        show_source(0)
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
