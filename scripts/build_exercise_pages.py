#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import markdown

GENERATED = Path("generated/exercises.json")
DIST = Path("dist")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[_\s]+", "-", value)
    value = re.sub(r"[^a-z0-9.-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def extract_section(body: str, heading: str) -> str:
    pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body)
    return match.group(1).strip() if match else ""


def markdown_body(note_path: Path) -> str:
    text = note_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return text


def root_url(repo_path: str) -> str:
    return "/" + repo_path.lstrip("/")


def render(item: dict) -> str:
    note_path = Path(item["note"])
    body = markdown_body(note_path)
    llm_comments = extract_section(body, "LLM Comments")
    my_thoughts = extract_section(body, "My Thoughts")

    source = html.escape(str(item.get("source", "")))
    subject = html.escape(str(item.get("subject", "")))
    topic = html.escape(str(item.get("topic", "")))
    chapter = html.escape(str(item.get("chapter", "")))
    exercise = html.escape(str(item.get("exercise", "")))
    outcome = html.escape(str(item.get("outcome", "")))
    created = html.escape(str(item.get("created", "")))
    raw_note = html.escape(root_url(item["note"]))

    blocks = []

    problem = item.get("problem_statement")
    if problem:
        p = html.escape(root_url(problem))
        blocks.append(
            '<section class="card">'
            '<div class="section-kicker">Problem</div>'
            f'<a href="{p}"><img class="exercise-image" src="{p}" alt="Problem statement"></a>'
            '</section>'
        )

    attempts = item.get("solution_attempts") or []
    if attempts:
        attempt_html = ['<section class="card"><div class="section-kicker">My work</div>']
        for i, ref in enumerate(attempts, start=1):
            u = html.escape(root_url(ref))
            attempt_html.append(
                f'<article class="attempt"><h3>Attempt {i}</h3>'
                f'<a href="{u}"><img class="exercise-image" src="{u}" '
                f'alt="Solution attempt {i}"></a></article>'
            )
        attempt_html.append("</section>")
        blocks.append("".join(attempt_html))

    if llm_comments:
        blocks.append(
            '<section class="card text-card">'
            '<div class="section-kicker">LLM review</div>'
            f'<div class="prose">{markdown.markdown(llm_comments)}</div>'
            '</section>'
        )

    if my_thoughts:
        blocks.append(
            '<section class="card text-card">'
            '<div class="section-kicker">My thoughts</div>'
            f'<div class="prose">{markdown.markdown(my_thoughts)}</div>'
            '</section>'
        )

    minutes = item.get("time_spent_min")
    minutes_html = f"<span>{html.escape(str(minutes))} min</span>" if minutes is not None else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{source} · Ch {chapter} · Ex {exercise} — SardineTrace</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <main class="exercise-page">
    <nav class="top-nav">
      <a href="/">← SardineTrace</a>
      <a href="{raw_note}">View raw Markdown</a>
    </nav>

    <header class="exercise-header">
      <p class="eyebrow">{subject} · {topic}</p>
      <h1>{source}</h1>
      <p class="lede">Chapter {chapter} · Exercise {exercise}</p>
      <div class="meta-row">
        <span class="badge">{outcome}</span>
        <span>{created}</span>
        {minutes_html}
      </div>
    </header>

    {''.join(blocks)}

    <footer class="exercise-footer">
      <a href="{raw_note}">View raw Markdown record</a>
    </footer>
  </main>
</body>
</html>
"""


def main() -> int:
    if not GENERATED.is_file():
        raise SystemExit("Run scripts/build_indexes.py first.")

    records = json.loads(GENERATED.read_text(encoding="utf-8"))

    for item in records:
        subject = slugify(item["subject"])
        source = slugify(item["source"])
        chapter = f'ch{item["chapter"]}'
        exercise = f'ex{item["exercise"]}'
        relative = f"exercise-pages/{subject}/{source}/{chapter}/{exercise}/"

        out_dir = DIST / relative
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render(item), encoding="utf-8")
        item["page_url"] = relative

    data_dir = DIST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "exercises.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(records)} human-facing exercise page(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
