#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path

EXERCISES_DIR = Path('exercises')
ALLOWED_OUTCOMES = {
    'not understood',
    'unsolved with guidance',
    'solved with guidance',
    'solved with mistakes',
    'solved',
}
REQUIRED_SCALARS = {'type','status','schema','created','source','subject','chapter','exercise','outcome'}
TOPIC_KEYS = ('topic','topics')

class ValidationError(Exception):
    pass

def strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in {'\'', '"'}:
        return v[1:-1]
    return v

def split_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise ValidationError('missing opening YAML delimiter')
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i]), '\n'.join(lines[i+1:])
    raise ValidationError('missing closing YAML delimiter')

def parse_frontmatter(fm: str):
    data, current = {}, None
    for raw in fm.splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        m = re.match(r'^\s+-\s+(.*)$', raw)
        if m and current:
            data.setdefault(current, []).append(strip_quotes(m.group(1)))
            continue
        m = re.match(r'^([A-Za-z0-9_-]+):(?:\s*(.*))?$', raw)
        if not m:
            current = None
            continue
        key, value = m.group(1), (m.group(2) or '').strip()
        if value == '':
            data[key] = []
            current = key
        else:
            data[key] = strip_quotes(value)
            current = None
    return data

def normalize_ref(v: str) -> str:
    v = strip_quotes(v)
    m = re.fullmatch(r'\[\[([^\]]+)\]\]', v)
    if m:
        v = m.group(1)
    return v.split('|',1)[0].split('#',1)[0].strip()

def validate_note(path: Path):
    errors = []
    try:
        fm, _ = split_frontmatter(path.read_text(encoding='utf-8'))
        meta = parse_frontmatter(fm)
    except Exception as exc:
        return {}, [str(exc)]

    for key in REQUIRED_SCALARS:
        value = meta.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f'missing/empty required field: {key}')

    if not any(isinstance(meta.get(k), str) and str(meta[k]).strip() for k in TOPIC_KEYS):
        errors.append('missing/empty required field: topic or topics')

    if meta.get('type') != 'exercise':
        errors.append(f"type must be 'exercise', got {meta.get('type')!r}")

    outcome = meta.get('outcome')
    if isinstance(outcome, str) and outcome not in ALLOWED_OUTCOMES:
        errors.append(f'invalid outcome: {outcome!r}; allowed: {", ".join(sorted(ALLOWED_OUTCOMES))}')

    problem = meta.get('problem_statement')
    if isinstance(problem, list):
        problem_refs = [str(x) for x in problem]
        if len(problem_refs) != 1:
            errors.append('problem_statement must contain exactly one file')
    elif isinstance(problem, str) and problem.strip():
        problem_refs = [problem]
    else:
        errors.append('problem_statement is missing/empty')
        problem_refs = []

    solutions = meta.get('solution_attempts')
    if not isinstance(solutions, list) or not solutions:
        errors.append('solution_attempts must contain at least one file')
        solution_refs = []
    else:
        solution_refs = [str(x) for x in solutions]

    for label, refs in [('problem_statement', problem_refs), ('solution_attempts', solution_refs)]:
        for ref in refs:
            target = normalize_ref(ref)
            asset = path.parent / target
            if not asset.is_file():
                errors.append(f'{label}: referenced file does not exist: {target}')
                continue
            if asset.suffix.lower() != '.webp':
                errors.append(f'{label}: expected .webp file: {target}')
            if asset.stat().st_size == 0:
                errors.append(f'{label}: file is empty: {target}')
    return meta, errors

def main() -> int:
    if not EXERCISES_DIR.is_dir():
        print('ERROR: exercises/ does not exist', file=sys.stderr)
        return 1
    notes = sorted(EXERCISES_DIR.rglob('*.md'))
    if not notes:
        print('ERROR: no exercise .md files found under exercises/', file=sys.stderr)
        return 1

    seen, failed = {}, False
    for note in notes:
        meta, errors = validate_note(note)
        if meta:
            source = str(meta.get('source','')).strip()
            chapter = str(meta.get('chapter','')).strip()
            exercise = str(meta.get('exercise','')).strip()
            attempt = str(meta.get('attempt','1')).strip() or '1'
            key = (source, chapter, exercise, attempt)
            if all(key[:3]):
                if key in seen:
                    errors.append(f'duplicate exercise key {key}; already used by {seen[key]}')
                else:
                    seen[key] = note
        if errors:
            failed = True
            print(f'\nFAIL {note}')
            for err in errors:
                print(f'  - {err}')
        else:
            print(f'OK   {note}')

    if failed:
        print('\nValidation failed.', file=sys.stderr)
        return 1
    print(f'\nValidated {len(notes)} exercise note(s).')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
