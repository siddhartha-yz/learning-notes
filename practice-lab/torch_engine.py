"""Execute student Python in bubblewrap; the GTK process never imports torch."""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
from core import save_json

RUNTIME = Path(os.environ.get('LEARNING_LAB_TORCH_RUNTIME', Path.home() / '.local/share/learning-notes-lab/torch-runtime'))


def run_code(lesson_id, source):
    if not (RUNTIME / 'bin/python').exists():
        raise ValueError('PyTorch 环境未安装，请运行 practice-lab/setup-torch.sh。')
    if len(source) > 30000:
        raise ValueError('本阶段代码请控制在 30000 字符以内。')
    with tempfile.TemporaryDirectory(prefix='torch-practice-') as temporary:
        root = Path(temporary)
        submission = root / 'submission'
        work = root / 'work'
        submission.mkdir(); work.mkdir()
        (submission / 'code.py').write_text(source)
        args = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
                '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/opt/runtime/bin:/usr/bin:/bin',
                '--setenv', 'LANG', 'C.UTF-8', '--setenv', 'OMP_NUM_THREADS', '1',
                '--setenv', 'OPENBLAS_NUM_THREADS', '1', '--setenv', 'MKL_NUM_THREADS', '1',
                '--ro-bind', '/usr', '/usr']
        for name in ['/bin', '/lib', '/lib64']:
            if Path(name).exists(): args += ['--ro-bind', name, name]
        args += ['--ro-bind', str(RUNTIME), '/opt/runtime', '--ro-bind', str(submission), '/submission',
                 '--ro-bind', str(Path(__file__).with_name('pytorch').resolve()), '/grader',
                 '--bind', str(work), '/work', '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev',
                 '--chdir', '/work', '/opt/runtime/bin/python', '-I', '/grader/grader.py', lesson_id]
        start = time.monotonic()
        with tempfile.TemporaryFile() as output:
            proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                proc.wait(timeout=25)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
                raise ValueError('运行超过 25 秒，已终止。请检查无限循环或过大的张量。')
            output.seek(0)
            log = output.read(16000).decode(errors='replace')
        path = work / 'result.json'
        if proc.returncode or not path.is_file() or path.is_symlink() or path.stat().st_size > 1024**2:
            raise ValueError('运行未完成，未判为通过。\n' + log[-4000:])
        result = json.loads(path.read_text())
        if type(result.get('passed')) is not bool or not isinstance(result.get('cases'), list):
            raise ValueError('测试结果无效，未判为通过。')
        result['elapsed_seconds'] = round(time.monotonic() - start, 2)
        return result


def save_attempt(directory, lesson, code, prediction, explanation, result, hints):
    from datetime import datetime, timezone
    from uuid import uuid4
    now = datetime.now(timezone.utc)
    path = directory / now.strftime('%Y-%m-%d') / (now.strftime('%H%M%S-') + uuid4().hex + '.json')
    save_json(path, dict(schema_version=2, kind='pytorch_submission', submitted_at=now.isoformat(),
                        status='submitted', lesson=lesson, code=code, prediction=prediction,
                        explanation=explanation, local_result=result, hint_level=hints))
    return path
