"""PyTorch learning surface embedded in the existing GTK desktop application."""
from pathlib import Path
import json

TUTORIALS = json.loads((Path(__file__).parent / "pytorch/tutorials.json").read_text())
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
        self.pages = Gtk.Notebook()
        self.pack_start(self.pages, True, True, 0)
        teaching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.pages.append_page(teaching, Gtk.Label(label='① 先学 · 讲解与实验'))
        self.teaching_text, scroll = editor(180)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        self.teaching_text.set_editable(False)
        teaching.pack_start(scroll, True, True, 0)
        teaching.pack_start(Gtk.Label(label='可修改的例子 · 直接运行即可，无需先答题', xalign=0), False, False, 0)
        self.demo_code, scroll = editor(160, True)
        self.demo_code.connect('key-press-event', self.indent)
        teaching.pack_start(scroll, True, True, 0)
        actions = Gtk.Box(spacing=8)
        self.demo_button = Gtk.Button(label='运行教学例子 · 本地执行')
        self.demo_button.connect('clicked', self.run_demo)
        self.restore_demo = Gtk.Button(label='恢复教学例子')
        self.restore_demo.connect('clicked', lambda *_: self.demo_code.get_buffer().set_text(TUTORIALS[self.lesson['id']]['code']))
        actions.pack_start(self.demo_button, True, True, 0)
        actions.pack_start(self.restore_demo, False, False, 0)
        teaching.pack_start(actions, False, False, 0)
        self.demo_output, scroll = editor(75, True)
        self.demo_output.set_editable(False)
        teaching.pack_start(scroll, False, False, 0)
        self.observation, scroll = editor(80)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        self.observation.set_editable(False)
        teaching.pack_start(scroll, False, False, 0)
        enter = Gtk.Button(label='理解例子后 → 进入独立练习（随时可返回讲解）')
        enter.get_style_context().add_class('primary')
        enter.connect('clicked', lambda *_: self.pages.set_current_page(1))
        teaching.pack_start(enter, False, False, 0)
        practice = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.pages.append_page(practice, Gtk.Label(label='② 练习 · 预测、实现与解释'))
        practice.pack_start(Gtk.Label(label='① 运行前预测 · 写下形状或数值，不必先写长篇解释', xalign=0), False, False, 0)
        self.prediction, scroll = editor(62)
        practice.pack_start(scroll, False, False, 0)
        practice.pack_start(Gtk.Label(label='② 独立实现 · Python / PyTorch · Tab 缩进，Enter 延续缩进', xalign=0), False, False, 0)
        self.code, scroll = editor(190, True)
        practice.pack_start(scroll, True, True, 0)
        self.code.connect('key-press-event', self.indent)
        self.run_button = Gtk.Button(label='运行测试 · 不调用 Agent')
        self.run_button.connect('clicked', self.run)
        practice.pack_start(self.run_button, False, False, 0)
        self.results, scroll = editor(90, True)
        self.results.set_editable(False)
        practice.pack_start(scroll, False, False, 0)
        practice.pack_start(Gtk.Label(label='③ 简短解释 · 解释轴与运算，若预测有误说明修正', xalign=0), False, False, 0)
        self.explanation, scroll = editor(62)
        practice.pack_start(scroll, False, False, 0)
        actions = Gtk.Box(spacing=8)
        self.submit_button = Gtk.Button(label='提交代码与解释给 Agent')
        self.submit_button.get_style_context().add_class('primary')
        self.submit_button.connect('clicked', self.submit)
        self.reset_button = Gtk.Button(label='重做本题')
        self.reset_button.connect('clicked', self.reset)
        actions.pack_start(self.submit_button, True, True, 0)
        actions.pack_start(self.reset_button, False, False, 0)
        practice.pack_start(actions, False, False, 0)
        for view in [self.code, self.prediction, self.explanation, self.demo_code]:
            view.get_buffer().connect('changed', self.changed)

    def draft_path(self):
        return self.state / 'pytorch-drafts' / (self.lesson['id'] + '.json')

    def changed(self, *_):
        if self.lesson and not self.loading:
            try:
                save_json(self.draft_path(), dict(code=text(self.code), prediction=text(self.prediction),
                    explanation=text(self.explanation), hint_level=self.hint_level, demo_code=text(self.demo_code)))
            except OSError:
                self.host.message('草稿保存失败，请检查本机状态目录权限。')

    def load(self, lesson):
        self.lesson = lesson
        draft = read_json(self.draft_path(), {})
        self.loading = True
        tutorial = TUTORIALS[lesson['id']]
        self.teaching_text.get_buffer().set_text(tutorial['title'] + '\n\n' + tutorial['lesson'])
        self.demo_code.get_buffer().set_text(draft.get('demo_code', tutorial['code']))
        self.demo_output.get_buffer().set_text('点击运行，查看真实输出。教学实验不计入题目通过状态。')
        self.observation.get_buffer().set_text('动手观察与修改\n' + tutorial['observe'])
        self.pages.set_current_page(0)
        self.code.get_buffer().set_text(draft.get('code', lesson['starter']))
        self.prediction.get_buffer().set_text(draft.get('prediction', ''))
        self.explanation.get_buffer().set_text(draft.get('explanation', ''))
        self.hint_level = draft.get('hint_level', 0)
        self.results.get_buffer().set_text('填写预测后运行。测试会显示具体失败输入与差异；基础语法可随时返回教学页查看；需要解题帮助时点击左侧提示。')
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
        for widget in [self.prediction, self.code, self.explanation, self.run_button, self.submit_button, self.reset_button, self.demo_code, self.demo_button, self.restore_demo]:
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

    def run_demo(self, *_):
        code = text(self.demo_code)
        path = save_attempt(core.ATTEMPTS, self.lesson, self.clean(code), '', '', None, self.hint_level)
        record = read_json(path, {})
        record.update(kind='pytorch_tutorial_run', tutorial=TUTORIALS[self.lesson['id']], passed=False)
        save_json(path, record)
        def done(result):
            result = self.clean_record(result)
            record.update(status='executed' if result['passed'] else 'execution_error', local_result=result)
            save_json(path, record)
            output = result['stdout'] or '程序已执行，没有 print 输出。'
            if not result['passed']:
                output += '\n' + result.get('error', '运行出错')
            self.demo_output.get_buffer().set_text(output)
            self.host.message('教学例子运行完成，可修改代码再观察；这不代表本题通过。' if result['passed'] else '例子运行出错，可对照讲解修改或恢复例子。')
        self.host.message('正在运行教学例子…')
        self.host.background(lambda: run_code(self.lesson['id'], code, tutorial=True), done,
                             on_error=lambda: finish_attempt(path, 'runtime_error'))

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
