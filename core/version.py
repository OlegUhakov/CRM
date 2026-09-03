from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent


def read_version():
    try:
        count = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            capture_output=True, text=True, cwd=BASE_DIR
        ).stdout.strip()
        return f'0.7.{count}'
    except Exception:
        return '0.7.0'
