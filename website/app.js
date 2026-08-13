async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
  return response.json();
}

function makeStat(label, value) {
  return `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`;
}

async function main() {
  const [analytics, exercises] = await Promise.all([
    loadJson("./data/analytics.json"),
    loadJson("./data/exercises.json"),
  ]);

  document.querySelector("#stats").innerHTML = [
    makeStat("Exercises", analytics.total_exercises),
    makeStat("Active days", analytics.active_days),
    makeStat("Minutes", analytics.total_time_spent_min),
  ].join("");

  const list = document.querySelector("#exercise-list");
  const recent = [...exercises].reverse().slice(0, 20);

  list.innerHTML = recent.length ? recent.map((item) => `
    <article class="exercise">
      <h3><a href="./${item.page_url}">${item.source} · Ch ${item.chapter} · Ex ${item.exercise}</a></h3>
      <p class="meta">${item.subject} · ${item.topic} · ${item.outcome}</p>
      <a href="./${item.page_url}">View exercise</a>
      · <a href="./${item.note}">Raw Markdown</a>
    </article>
  `).join("") : "<p>No exercises published yet.</p>";
}

main().catch((error) => {
  console.error(error);
  document.querySelector("#exercise-list").innerHTML =
    `<p>Failed to load SardineTrace data: ${error.message}</p>`;
});
