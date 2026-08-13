async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
  return response.json();
}
function stat(label, value) {
  return `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`;
}
async function main() {
  const [analytics, exercises] = await Promise.all([
    loadJson('./data/analytics.json'),
    loadJson('./data/exercises.json'),
  ]);
  document.querySelector('#stats').innerHTML = [
    stat('Exercises', analytics.total_exercises),
    stat('Active days', analytics.active_days),
    stat('Minutes', analytics.total_time_spent_min),
  ].join('');

  const recent = [...exercises].reverse().slice(0, 20);
  document.querySelector('#exercise-list').innerHTML = recent.length ? recent.map(item => `
    <article class="exercise">
      <h3>${item.source} · Ch ${item.chapter} · Ex ${item.exercise}</h3>
      <p class="meta">${item.subject} · ${item.topic} · ${item.outcome}</p>
      <a href="./${item.note}">Markdown</a>
      ${item.problem_statement ? ` · <a href="./${item.problem_statement}">Problem</a>` : ''}
      ${item.solution_attempts?.[0] ? ` · <a href="./${item.solution_attempts[0]}">Attempt</a>` : ''}
    </article>
  `).join('') : '<p>No exercises published yet.</p>';
}
main().catch(err => {
  console.error(err);
  document.querySelector('#exercise-list').innerHTML = `<p>Failed to load data: ${err.message}</p>`;
});
