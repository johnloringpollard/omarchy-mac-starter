#!/usr/bin/env python3
"""Check the publishable tree for accidental private exports and invalid data."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BINARY_ASSETS = {'assets/fonts/Inter.ttc', 'assets/theme/backgrounds/01-silver-coast.png'}
FORBIDDEN_COMPONENTS = {'.ssh', '.aws', '.kube', 'credentials.json', 'bridge.conf',
                        'AirPodsTrayApp', 'accounts', '.env', 'journal.json', 'progress.json',
                        'node_modules', '__pycache__', 'backups'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'fixed home directory': re.compile(r'/(?:home|Users)/[A-Za-z][A-Za-z0-9_.-]*/'),
    'Bluetooth address': re.compile(r'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'),
    'private IPv4 address': re.compile(r'\b(?:192\.168|10\.\d{1,3})\.\d{1,3}\.\d{1,3}\b'),
}


def main():
    output = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    names = sorted(set(n.decode() for n in output.split(b'\0') if n))
    errors = []
    for name in names:
        path = ROOT / name
        if path.is_symlink():
            errors.append(f'{name}: symlinks are not part of this export')
            continue
        if FORBIDDEN_COMPONENTS.intersection(path.relative_to(ROOT).parts):
            errors.append(f'{name}: private/generated path')
        try:
            content = path.read_bytes()
            if name in BINARY_ASSETS:
                continue
            text = content.decode('utf-8')
            for label, pattern in PATTERNS.items():
                if pattern.search(text):
                    errors.append(f'{name}: possible {label}')
            if path.suffix == '.py':
                ast.parse(text, filename=name)
            elif path.suffix == '.json':
                json.loads(text)
            elif path.suffix == '.toml':
                tomllib.loads(text)
            elif path.suffix in ('.svg',) or name.endswith('apple-ui.conf'):
                ET.fromstring(text)
        except (UnicodeError, OSError, ValueError, SyntaxError, ET.ParseError) as error:
            errors.append(f'{name}: {error}')
    lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
    for module in lock['modules'].values():
        for patch in module['patches']:
            actual = hashlib.sha256((ROOT / patch['path']).read_bytes()).hexdigest()
            if actual != patch['sha256']:
                errors.append(f'{patch["path"]}: checksum mismatch')
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f'PASS: {len(names)} publishable files; syntax, patch checksums, and private-data patterns checked.')
    print('Pattern checks supplement an explicit export allowlist; they do not prove all content is non-sensitive.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
