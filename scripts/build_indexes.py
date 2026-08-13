#!/usr/bin/env python3
from __future__ import annotations
import json, re
from collections import Counter, defaultdict
from pathlib import Path

EXERCISES_DIR = Path('exercises')
GENERATED_DIR = Path('generated')

def strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in {'\'', '"'}:
        return v[1:-1]
    return v

def split_frontmatter(text: str):
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return '\n'.join(lines[1:i]), '\n'.join(lines[i+1:])
    raise ValueError('invalid YAML frontmatter')

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

def to_int(v):
    if v in (None, '', []): return None
    try: return int(str(v))
    except ValueError: return None

def record(note: Path):
    text = note.read_text(encoding='utf-8')
    fm, body = split_frontmatter(text)
    meta = parse_frontmatter(fm)
    topic = meta.get('topic') or meta.get('topics') or ''
    problem = meta.get('problem_statement')
    if isinstance(problem, list):
        problem = problem[0] if problem else ''
    problem = normalize_ref(str(problem or ''))
    attempts = meta.get('solution_attempts')
    attempts = [normalize_ref(str(x)) for x in attempts] if isinstance(attempts, list) else []
    created = str(meta.get('solved_at') or meta.get('created') or '')
    base = note.parent
    return {
        'source': str(meta.get('source','')),
        'subject': str(meta.get('subject','')),
        'topic': str(topic),
        'chapter': str(meta.get('chapter','')),
        'exercise': str(meta.get('exercise','')),
        'attempt': to_int(meta.get('attempt')) or 1,
        'outcome': str(meta.get('outcome','')),
        'created': str(meta.get('created','')),
        'activity_date': created[:10] if created else '',
        'time_spent_min': to_int(meta.get('time_spent_min')),
        'note': note.as_posix(),
        'problem_statement': (base / problem).as_posix() if problem else '',
        'solution_attempts': [(base / x).as_posix() for x in attempts],
        'llm_comments_present': '## LLM Comments' in body and bool(body.split('## LLM Comments',1)[1].split('##',1)[0].strip()),
        'my_thoughts_present': '## My Thoughts' in body and bool(body.split('## My Thoughts',1)[1].split('##',1)[0].strip()),
    }

def write(name, data):
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / name
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {path}')

def main():
    records = [record(p) for p in sorted(EXERCISES_DIR.rglob('*.md'))]
    records.sort(key=lambda r: (r['activity_date'], r['source'], r['chapter'], r['exercise']))
    write('exercises.json', records)

    activity = defaultdict(lambda: {'count':0,'time_spent_min':0,'exercises':[]})
    for r in records:
        day = r['activity_date']
        if not day: continue
        b = activity[day]
        b['count'] += 1
        b['time_spent_min'] += r['time_spent_min'] or 0
        b['exercises'].append({k:r[k] for k in ['subject','topic','source','chapter','exercise','outcome','note']})
    write('activity.json', dict(sorted(activity.items())))

    topics = defaultdict(lambda: {'count':0,'sources':set(),'exercises':[]})
    for r in records:
        key = (r['subject'], r['topic'])
        b = topics[key]
        b['count'] += 1
        b['sources'].add(r['source'])
        b['exercises'].append({k:r[k] for k in ['source','chapter','exercise','outcome','note']})
    topics_out = [
        {'subject':s,'topic':t,'count':b['count'],'sources':sorted(b['sources']),'exercises':b['exercises']}
        for (s,t), b in sorted(topics.items())
    ]
    write('topics.json', topics_out)

    write('analytics.json', {
        'total_exercises': len(records),
        'active_days': len({r['activity_date'] for r in records if r['activity_date']}),
        'total_time_spent_min': sum(r['time_spent_min'] or 0 for r in records),
        'outcomes': dict(sorted(Counter(r['outcome'] for r in records).items())),
        'subjects': dict(sorted(Counter(r['subject'] for r in records).items())),
        'sources': dict(sorted(Counter(r['source'] for r in records).items())),
    })
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
