"""PyTorch learning surface embedded in the existing GTK desktop application."""
from pathlib import Path
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import core
from core import save_json, read_json, finish_attempt, review, review_message
from torch_engine import run_code, save_attempt


def text(view):
    b = view.get_buffer()
    return b.get_text(b.get_start_iter(), b.get_end_iter(), False)


def editor(height, mono=False):
    view = Gtk.TextView(wrap_mode=Gtk.WrapMode.NONE if mono else Gtk.WrapMode.WORD_CHAR)
    view.set_left_margin(10); view.set_top_margin(8)
    if mono:
        view.set_monospace(True)
        view.get_style_context().add_class('terminal')
    scroll = Gtk.ScrolledWindow()
    scroll.set_min_content_height(height)
    scroll.add(view)
    return view, scroll


class TorchPanel(Gtk.Box):
    def __init__(self, host, state):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.host, self.state = host, state
        self.lesson = None
        self.loading = False
        self.hint_level = 0
        self.last_code = None
        self.result = None
        self.last_prediction = None
        self.pack_start(Gtk.Label(label='① 运行前预测 · 写下形状或数值，不必先写长篇解释', xalign=0), False, False, 0)
        self.prediction, scroll = editor(62)
        self.pack_start(scroll, False, False, 0)
        self.pack_start(Gtk.Label(label='② 独立实现 · Python / PyTorch · Tab 缩进，Enter 延续缩进', xalign=0), False, False, 0)
        self.code, scroll = editor(190, True)
        self.pack_start(scroll, True, True, 0)
        self.code.connect('key-press-event', self.indent)
        self.run_button = Gtk.Button(label='运行测试 · 不调用 Agent')
        self.run_button.connect('clicked', self.run)
        self.pack_start(self.run_button, False, False, 0)
        self.results, scroll = editor(90, True)
        self.results.set_editable(False)
        self.pack_start(scroll, False, False, 0)
        self.pack_start(Gtk.Label(label='③ 简短解释 · 解释轴与运算，若预测有误说明修正', xalign=0), False, False, 0)
        self.explanation, scroll = editor(62)
        self.pack_start(scroll, False, False, 0)
        actions = Gtk.Box(spacing=8)
        self.submit_button = Gtk.Button(label='提交代码与解释给 Agent')
        self.submit_button.get_style_context().add_class('primary')
        self.submit_button.connect('clicked', self.submit)
        self.reset_button = Gtk.Button(label='重做本题')
        self.reset_button.connect('clicked', self.reset)
        actions.pack_start(self.submit_button, True, True, 0)
        actions.pack_start(self.reset_button, False, False, 0)
        self.pack_start(actions, False, False, 0)
        for view in [self.code, self.prediction, self.explanation]:
            view.get_buffer().connect('changed', self.changed)

    def draft_path(self):
        return self.state / 'pytorch-drafts' / (self.lesson['id'] + '.json')

    def changed(self, *_):
        if self.lesson and not self.loading:
            try:
                save_json(self.draft_path(), dict(code=text(self.code), prediction=text(self.prediction),
                    explanation=text(self.explanation), hint_level=self.hint_level))
            except OSError:
                self.host.message('草稿保存失败，请检查本机状态目录权限。')

    def load(self, lesson):
        self.lesson = lesson
        draft = read_json(self.draft_path(), {})
        self.loading = True
        self.code.get_buffer().set_text(draft.get('code', lesson['starter']))
        self.prediction.get_buffer().set_text(draft.get('prediction', ''))
        self.explanation.get_buffer().set_text(draft.get('explanation', ''))
        self.hint_level = draft.get('hint_level', 0)
        self.results.get_buffer().set_text('填写预测后运行。测试会显示具体失败输入与差异；API 用法可主动点击左侧提示。')
        self.result = None; self.last_code = None
        self.loading = False

    def reset(self, *_):
        self.draft_path().unlink(missing_ok=True)
        self.load(self.lesson)
        self.host.message('已恢复函数签名；历史通过记录保留，当前草稿需要重新测试。')

    def hint(self):
        hints = self.lesson['hints']
        self.hint_level = min(self.hint_level + 1, len(hints))
        self.changed()
        self.host.message(f'提示 {self.hint_level}/{len(hints)}：' + hints[self.hint_level - 1])

    def set_busy(self, busy):
        for widget in [self.prediction, self.code, self.explanation, self.run_button, self.submit_button, self.reset_button]:
            widget.set_sensitive(not busy)

    def indent(self, view, event):
        key = Gdk.keyval_name(event.keyval)
        buffer = view.get_buffer()
        if key == 'Tab':
            buffer.insert_at_cursor('    ')
            return True
        if key == 'Return':
            cursor = buffer.get_iter_at_mark(buffer.get_insert())
            start = cursor.copy(); start.set_line_offset(0)
            line = buffer.get_text(start, cursor, False)
            spaces = len(line) - len(line.lstrip(' '))
            buffer.insert_at_cursor('\n' + ' ' * (spaces + (4 if line.rstrip().endswith(':') else 0)))
            return True
        return False

    def clean(self, value):
        return value.replace(self.host.key, '[REDACTED]') if self.host.key else value

    def clean_record(self, value):
        if isinstance(value, str):
            return self.clean(value)
        if isinstance(value, dict):
            return {k: self.clean_record(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.clean_record(v) for v in value]
        return value

    def run(self, *_):
        if not text(self.prediction).strip():
            self.host.message('先写下你对题目例子的预测，再运行验证；预测错了可以在解释中修正。')
            return
        code = text(self.code)
        prediction = text(self.prediction)
        path = save_attempt(core.ATTEMPTS, self.lesson, self.clean(code), self.clean(prediction),
                            self.clean(text(self.explanation)), None, self.hint_level)
        record = read_json(path, {}); record['kind'] = 'pytorch_run'; save_json(path, record)
        def done(result):
            result = self.clean_record(result)
            self.result = result; self.last_code = code; self.last_prediction = prediction
            record = read_json(path, {}); record.update(status='tested', local_result=result)
            save_json(path, record)
            lines = []
            for case in result['cases']:
                lines.append(('✓ ' if case['passed'] else '✗ ') + case['name'])
                if not case['passed']:
                    lines.extend([case['detail'], '输入：' + case.get('inputs', ''),
                                  '预期：' + case.get('expected', ''), '实际：' + case.get('actual', '')])
            if result['stdout']: lines.extend(['\n你的输出：', result['stdout']])
            self.results.get_buffer().set_text('\n'.join(lines))
            self.host.message('本地测试通过，请补充解释后提交。' if result['passed'] else '本地测试未全部通过，请根据反例修改。')
        self.host.message('正在隔离环境中运行 PyTorch…')
        self.host.background(lambda: run_code(self.lesson['id'], code), done,
                             on_error=lambda: finish_attempt(path, 'runtime_error'))

    def submit(self, *_):
        if self.result is None or self.last_code != text(self.code):
            self.host.message('当前代码尚未测试或已更改，请先运行测试。')
            return
        if not self.result['passed']:
            self.host.message('请先修正未通过的本地测试；本次不调用 Agent。')
            return
        explanation = text(self.explanation).strip()
        if not explanation:
            self.host.message('请写下本题要求的简短解释，再提交。')
            return
        code, prediction = text(self.code), self.last_prediction
        path = save_attempt(core.ATTEMPTS, self.lesson, self.clean(code), self.clean(prediction),
                            self.clean(explanation), self.result, self.hint_level)
        if not self.host.key or not self.host.config.get('base_url') or not self.host.config.get('model'):
            finish_attempt(path, 'api_not_configured')
            self.host.message('本地测试已通过；请配置 API 完成解释评审。提交记录已保存。')
            return
        evidence = [{'code': self.clean(code), 'prediction': self.clean(prediction), 'tests': self.result}]
        local = [(case['name'], case['passed']) for case in self.result['cases']]
        lesson = dict(self.lesson)
        lesson['rubric'] += ' 初始预测可出错，若最终解释已正确修正，不因初次预测错误拒绝通过。只判断解释，不要求特定API或禁止正确循环。'
        config, key = dict(self.host.config), self.host.key
        def done(result):
            finish_attempt(path, 'reviewed', result, result['passed'])
            self.host.progress[self.lesson['id']] = {'passed': result['passed'], 'feedback': result['feedback']}
            save_json(self.state / 'progress.json', self.host.progress)
            self.host.update_completion()
            self.host.message(review_message(result['passed'], result))
        self.host.message('Agent 正在核对本题预测、代码与解释…')
        self.host.background(lambda: review(config, key, lesson, evidence, self.clean(explanation), local), done,
                             on_error=lambda: finish_attempt(path, 'api_error'))
