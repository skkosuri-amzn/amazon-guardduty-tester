#!/usr/bin/env python3
#Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the "license" file accompanying this file. This file is distributed
#  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing
#  permissions and limitations under the License.

'''
Lint agent skill markdown (Claude SKILL.md and Kiro steering docs).

Checks that each file has a valid YAML frontmatter block with the fields the
host expects, a kebab-case name (Claude), and body content. Uses PyYAML when
available, otherwise a minimal key: value fallback parser.

Usage:
    python3 lint_skill.py                 # lint all known skills under skills/
    python3 lint_skill.py <file> [<file>] # lint specific files
'''

import os
import re
import sys
from typing import Dict, List, Tuple


def _parse_frontmatter(text: str) -> Tuple[Dict, str, List[str]]:
    '''Return (frontmatter dict, body, errors). Frontmatter must be at the top.'''
    errors: List[str] = []
    match = re.match(r'^---\n(.*?)\n---\n?', text, re.DOTALL)
    if not match:
        return {}, text, ['no YAML frontmatter block (--- ... ---) at top of file']

    raw = match.group(1)
    body = text[match.end():].strip()

    try:
        import yaml
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            errors.append('frontmatter did not parse to a mapping')
            data = {}
    except ModuleNotFoundError:
        # Minimal fallback: top-level "key: value" lines only.
        data = {}
        for line in raw.splitlines():
            if line and not line.startswith((' ', '\t')) and ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()

    return data, body, errors


def _is_kebab_case(value: str) -> bool:
    return bool(re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', value))


def lint_claude(path: str) -> List[str]:
    '''Lint a Claude SKILL.md: requires kebab-case name + description + body.'''
    text = open(path, encoding='utf-8').read()
    fm, body, errors = _parse_frontmatter(text)
    if errors:
        return errors

    name = str(fm.get('name', '') or '')
    desc = str(fm.get('description', '') or '')

    if not name:
        errors.append('missing required field: name')
    elif not _is_kebab_case(name):
        errors.append(f'name not kebab-case: {name!r}')

    if not desc:
        errors.append('missing required field: description')
    elif len(desc) > 1024:
        errors.append(f'description very long ({len(desc)} chars)')

    if not body:
        errors.append('no body content after frontmatter')

    return errors


def lint_kiro(path: str) -> List[str]:
    '''
    Lint a Kiro steering doc: frontmatter is optional, but if present and it has
    an `inclusion` key the value must be one of the supported modes. Body required.
    '''
    text = open(path, encoding='utf-8').read()
    errors: List[str] = []

    if text.lstrip().startswith('---'):
        fm, body, fm_errors = _parse_frontmatter(text)
        errors.extend(fm_errors)
        inclusion = fm.get('inclusion')
        if inclusion is not None and str(inclusion) not in ('always', 'fileMatch', 'manual'):
            errors.append(f'invalid inclusion mode: {inclusion!r}')
    else:
        body = text.strip()

    if not body:
        errors.append('no body content')

    return errors


# (path, linter) pairs relative to this file's directory.
DEFAULT_TARGETS = [
    ('claude/guardduty-investigation/SKILL.md', lint_claude),
    ('kiro/guardduty-investigation/guardduty-investigation.md', lint_kiro),
]


def _choose_linter(path: str):
    base = os.path.basename(path)
    if base == 'SKILL.md' or os.sep + 'claude' + os.sep in path:
        return lint_claude
    return lint_kiro


def main(argv: List[str]) -> int:
    here = os.path.dirname(os.path.abspath(__file__))

    if argv:
        targets = [(p, _choose_linter(p)) for p in argv]
    else:
        targets = [(os.path.join(here, rel), fn) for rel, fn in DEFAULT_TARGETS]

    failures = 0
    for path, linter in targets:
        rel = os.path.relpath(path)
        if not os.path.isfile(path):
            print(f'FAIL {rel}: file not found')
            failures += 1
            continue
        errors = linter(path)
        if errors:
            failures += 1
            print(f'FAIL {rel}:')
            for err in errors:
                print(f'  - {err}')
        else:
            print(f'OK   {rel}')

    print()
    print(f'{len(targets) - failures}/{len(targets)} skill file(s) passed.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
