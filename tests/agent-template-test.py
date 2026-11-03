#!/usr/bin/env python3
"""Generate a throwaway agent from series/_template and validate the skeleton."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
GENERATOR = os.path.join(ROOT, 'series', 'new-agent.py')


def main():
    tmp = tempfile.mkdtemp(prefix='agent-template-')
    dest = os.path.join(tmp, 'test-agent')
    try:
        result = subprocess.run(
            [sys.executable, GENERATOR, 'test-agent', '--name', 'Test Agent',
             '--title', 'Blank series agent', '--dest', dest],
            capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        required = [
            'test-agent.md', 'test-agent-core.md', 'test-agent-voice.md', 'AGENTS.md',
            'INDEX.md', 'SOUL.md', 'IDENTITY.md', 'TOOLS.md', 'README.md',
            'RELEASE.md', 'setup.sh', '.gitignore',
            'core/guardrails.md', 'core/relationships.md', 'core/arcs.md',
            'core/voice-calibration.md', 'world/factions.md',
            'reference/knowledge-web.md', 'tests/master-audit.sh',
            'tests/module-test.sh', 'tests/quote-verify.sh',
            '.github/workflows/ci.yml',
        ]
        for rel in required:
            assert os.path.isfile(os.path.join(dest, rel)), f'missing {rel}'
        for root, _dirs, files in os.walk(dest):
            for name in files:
                if name.endswith(('.md', '.sh', '.py', '.yml')):
                    text = open(os.path.join(root, name), encoding='utf-8').read()
                    left = re.findall(r'\{\{[a-z0-9_]+\}\}', text)
                    assert not left, f'unresolved placeholders in {name}: {left}'
        entry = open(os.path.join(dest, 'test-agent.md'), encoding='utf-8').read()
        assert 'mode: primary' in entry and 'Test Agent' in entry
        assert 'Token Estimate:' in entry

        env = dict(os.environ, WORKSPACE=dest, LORE=ROOT)
        module = subprocess.run(['bash', os.path.join(dest, 'tests', 'module-test.sh')],
                                capture_output=True, text=True, env=env)
        assert module.returncode == 0, module.stdout + module.stderr

        duplicate = subprocess.run(
            [sys.executable, GENERATOR, 'test-agent', '--name', 'X', '--title', 'Y',
             '--dest', dest], capture_output=True, text=True)
        assert duplicate.returncode != 0, 'generator overwrote an existing agent'
        invalid = subprocess.run(
            [sys.executable, GENERATOR, '../evil', '--name', 'X', '--title', 'Y',
             '--dest', os.path.join(tmp, 'evil')], capture_output=True, text=True)
        assert invalid.returncode != 0, 'generator accepted a traversing id'

        print('agent template: generated and validated')
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
