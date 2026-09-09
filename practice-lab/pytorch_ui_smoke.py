"""Real PyTorch + GTK; model responses mocked; all user state is temporary."""
from pathlib import Path
import tempfile
from unittest.mock import patch
import app
import core
import torch_panel
from test_pytorch import SOLUTIONS
from ui_smoke import settle
from gi.repository import Gtk


def main():
    Gtk.Settings.get_default().set_property('gtk-enable-animations', False)
    with tempfile.TemporaryDirectory() as temporary, \
         patch.object(app, 'STATE', Path(temporary) / 'state'), \
         patch.object(core, 'ATTEMPTS', Path(temporary) / 'attempts'), \
         patch.object(torch_panel, 'review', return_value={'passed': True, 'feedback': '本题回答正确，已通过。', 'next_step': ''}) as reviewer:
        window = app.Lab(); window.show_all()
        try:
            window.config = {'base_url': 'https://example.com/v1', 'model': 'mock'}
            window.key = 'synthetic-secret'
            window.track_selector.set_active(window.tracks.index('PyTorch'))
            panel = window.torch_panel
            assert len(window.chapter_selector.get_model()) == 3
            assert len(window.selector.get_model()) == 2
            assert panel.hint_level == 0
            panel.run_button.emit('clicked')
            assert not window.busy
            assert not list(core.ATTEMPTS.rglob('*.json'))
            assert panel.pages.get_current_page() == 0
            assert 'torch.tensor' in torch_panel.text(panel.teaching_text)
            panel.demo_code.get_buffer().set_text('print("demo edited")')
            panel.demo_button.emit('clicked'); settle(window)
            assert 'demo edited' in torch_panel.text(panel.demo_output)
            assert not window.progress.get(panel.lesson['id'], {}).get('passed')
            assert panel.result is None
            assert reviewer.call_count == 0
            panel.load(panel.lesson)
            assert torch_panel.text(panel.demo_code) == 'print("demo edited")'
            panel.restore_demo.emit('clicked')
            assert 'import torch' in torch_panel.text(panel.demo_code)
            panel.pages.set_current_page(1)
            for index, lesson in [(i, l) for i, l in enumerate(app.LESSONS) if l['track'] == 'PyTorch']:
                window.select_lesson(index)
                panel.prediction.get_buffer().set_text('UI 测试预测；非学生作答。')
                panel.code.get_buffer().set_text('import torch\n' + SOLUTIONS[lesson['id']])
                panel.explanation.get_buffer().set_text('UI 测试解释；Agent 已模拟。')
                panel.run_button.emit('clicked'); settle(window)
                assert panel.result and panel.result['passed'], panel.result
                if lesson['id'] == 'torch-batch':
                    window.hint()
                    assert panel.hint_level == 1
                    reviewer.return_value = {'passed': False, 'feedback': '模拟：请解释样本轴。', 'next_step': ''}
                    panel.submit_button.emit('clicked'); settle(window)
                    assert not window.progress[lesson['id']]['passed']
                    reviewer.return_value = {'passed': True, 'feedback': '本题回答正确，已通过。', 'next_step': ''}
                panel.submit_button.emit('clicked'); settle(window)
                assert window.progress[lesson['id']]['passed']
                panel.code.get_buffer().insert_at_cursor('\n# 草稿变化\n')
                before = reviewer.call_count
                panel.submit_button.emit('clicked')
                assert reviewer.call_count == before
            assert '全部完成' in window.lesson_status.get_text()
            assert not window.next_button.get_visible()
            window.track_selector.set_active(window.tracks.index('Linux'))
            assert window.content_stack.get_visible_child_name() == 'linux'
            window.track_selector.set_active(window.tracks.index('PyTorch'))
            assert 'build_batch' in torch_panel.text(panel.code)
            assert panel.hint_level == 1
            assert panel.result is None
            logs = [core.read_json(p, {}) for p in core.ATTEMPTS.rglob('*.json')]
            demos = [l for l in logs if l['kind'] == 'pytorch_tutorial_run']
            assert len(demos) == 1 and demos[0]['passed'] is False
            assert demos[0]['local_result']['passed'] is True
            assert len([l for l in logs if l['kind'] == 'pytorch_run']) == 6
            assert len([l for l in logs if l['kind'] == 'pytorch_submission']) == 7
            assert all('code' in l and 'prediction' in l for l in logs)
            assert any(l.get('review', {}).get('passed') is False for l in logs if l.get('review'))
            print('PyTorch GTK passed: 6 real exercises, explicit hints, drafts, stale-code guard, mock review retry, 14 logs including ungraded tutorial, default teaching, demo draft restore, track switching')
        finally:
            window.session.close(); window.destroy()


if __name__ == '__main__': main()
