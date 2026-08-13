const WEEK_COUNT = 53;
const DAY_COUNT = WEEK_COUNT * 7;

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function makeStat(label, value) {
  return `<div class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
}

function parseDate(date) {
  return new Date(`${date}T00:00:00`);
}

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function displayDate(date) {
  return parseDate(date).toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function activityRange(exercises) {
  const dated = exercises
    .map((item) => item.activity_date)
    .filter(Boolean)
    .sort();
  const latestActivity = dated.length ? parseDate(dated.at(-1)) : new Date();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const reference = latestActivity > today ? latestActivity : today;
  const weekEnd = new Date(reference);
  weekEnd.setDate(weekEnd.getDate() + (6 - weekEnd.getDay()));
  const start = new Date(weekEnd);
  start.setDate(start.getDate() - (DAY_COUNT - 1));
  return { start, reference };
}

function groupByDate(exercises) {
  const grouped = new Map();
  exercises.forEach((item) => {
    if (!item.activity_date) return;
    const day = grouped.get(item.activity_date) || [];
    day.push(item);
    grouped.set(item.activity_date, day);
  });
  return grouped;
}

function activityLevel(count) {
  if (count === 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count <= 4) return 3;
  return 4;
}

function monthLabels(start) {
  const labels = [];
  let previousMonth = -1;
  for (let week = 0; week < WEEK_COUNT; week += 1) {
    const date = new Date(start);
    date.setDate(start.getDate() + week * 7);
    const month = date.getMonth();
    const show = month !== previousMonth && (week === 0 || date.getDate() <= 7);
    labels.push(show ? date.toLocaleDateString(undefined, { month: "short" }) : "");
    previousMonth = month;
  }
  return labels;
}

function renderHeatmap(container, exercises, range, onSelect) {
  const grouped = groupByDate(exercises);
  const shell = document.createElement("div");
  shell.className = "heatmap-scroll";

  const calendar = document.createElement("div");
  calendar.className = "heatmap-calendar";

  const months = document.createElement("div");
  months.className = "heatmap-months";
  monthLabels(range.start).forEach((label) => {
    const span = document.createElement("span");
    span.textContent = label;
    months.append(span);
  });

  const dayLabels = document.createElement("div");
  dayLabels.className = "heatmap-day-labels";
  ["", "Mon", "", "Wed", "", "Fri", ""].forEach((label) => {
    const span = document.createElement("span");
    span.textContent = label;
    dayLabels.append(span);
  });

  const grid = document.createElement("div");
  grid.className = "heatmap-grid";
  for (let index = 0; index < DAY_COUNT; index += 1) {
    const date = new Date(range.start);
    date.setDate(range.start.getDate() + index);
    const key = dateKey(date);
    const count = (grouped.get(key) || []).length;
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "heatmap-cell";
    cell.dataset.level = activityLevel(count);
    cell.dataset.date = key;
    cell.title = `${count} exercise${count === 1 ? "" : "s"} on ${displayDate(key)}`;
    cell.setAttribute("aria-label", cell.title);
    if (date > range.reference) {
      cell.disabled = true;
      cell.classList.add("is-future");
    } else {
      cell.addEventListener("click", () => {
        grid.querySelector(".is-selected")?.classList.remove("is-selected");
        cell.classList.add("is-selected");
        onSelect(key, grouped.get(key) || []);
      });
    }
    grid.append(cell);
  }

  const legend = document.createElement("div");
  legend.className = "heatmap-legend";
  legend.innerHTML = `<span>Less</span>${[0, 1, 2, 3, 4]
    .map((level) => `<i class="heatmap-cell" data-level="${level}"></i>`)
    .join("")}<span>More</span>`;

  calendar.append(months, dayLabels, grid);
  shell.append(calendar);
  container.replaceChildren(shell, legend);
}

function exerciseLink(item) {
  return `
    <article class="exercise compact-exercise">
      <h3><a href="./${escapeHtml(item.page_url)}">${escapeHtml(item.source)} · Ch ${escapeHtml(item.chapter)} · Ex ${escapeHtml(item.exercise)}</a></h3>
      <p class="meta">${escapeHtml(item.subject)} · ${escapeHtml(item.topic)} · ${escapeHtml(item.outcome)}</p>
    </article>`;
}

function renderDayDetails(container, date, exercises, context) {
  container.innerHTML = `
    <div class="day-details-heading">
      <div>
        <p class="eyebrow">${escapeHtml(context)}</p>
        <h3>${escapeHtml(displayDate(date))}</h3>
      </div>
      <strong>${exercises.length} exercise${exercises.length === 1 ? "" : "s"}</strong>
    </div>
    <div class="day-exercise-list">
      ${exercises.length ? exercises.map(exerciseLink).join("") : "<p class=\"empty-state\">No exercises recorded on this day.</p>"}
    </div>`;
}

function latestActiveDate(exercises) {
  return exercises.map((item) => item.activity_date).filter(Boolean).sort().at(-1);
}

function selectHeatmapDate(container, date) {
  if (!date) return;
  container.querySelector(`[data-date="${date}"]`)?.classList.add("is-selected");
}

function setupAreaActivity(exercises, range) {
  const selector = document.querySelector("#area-selector");
  const heatmap = document.querySelector("#area-heatmap");
  const details = document.querySelector("#area-day-details");
  const areas = [...new Set(exercises.map((item) => item.subject).filter(Boolean))]
    .sort((a, b) => a.localeCompare(b));

  if (!areas.length) {
    selector.innerHTML = "<p>No areas published yet.</p>";
    heatmap.replaceChildren();
    return;
  }

  function chooseArea(area) {
    const filtered = exercises.filter((item) => item.subject === area);
    selector.querySelectorAll("button").forEach((button) => {
      const selected = button.dataset.area === area;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    renderHeatmap(heatmap, filtered, range, (date, items) => {
      renderDayDetails(details, date, items, area);
    });
    const latest = latestActiveDate(filtered);
    if (latest) {
      selectHeatmapDate(heatmap, latest);
      renderDayDetails(details, latest, groupByDate(filtered).get(latest) || [], area);
    } else {
      details.replaceChildren();
    }
  }

  areas.forEach((area) => {
    const count = exercises.filter((item) => item.subject === area).length;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "area-button";
    button.dataset.area = area;
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = `<span>${escapeHtml(area)}</span><strong>${count}</strong>`;
    button.addEventListener("click", () => chooseArea(area));
    selector.append(button);
  });

  chooseArea(areas[0]);
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
    makeStat("Areas", Object.keys(analytics.subjects || {}).length),
  ].join("");

  const range = activityRange(exercises);
  const allHeatmap = document.querySelector("#all-heatmap");
  const allDetails = document.querySelector("#all-day-details");
  renderHeatmap(allHeatmap, exercises, range, (date, items) => {
    renderDayDetails(allDetails, date, items, "All areas");
  });
  const exerciseCount = analytics.total_exercises;
  const areaCount = Object.keys(analytics.subjects || {}).length;
  document.querySelector("#all-activity-summary").textContent = `${exerciseCount} exercise${exerciseCount === 1 ? "" : "s"} across ${areaCount} area${areaCount === 1 ? "" : "s"}`;

  const latest = latestActiveDate(exercises);
  if (latest) {
    selectHeatmapDate(allHeatmap, latest);
    renderDayDetails(allDetails, latest, groupByDate(exercises).get(latest) || [], "All areas");
  }

  setupAreaActivity(exercises, range);

  const list = document.querySelector("#exercise-list");
  const recent = [...exercises].reverse().slice(0, 20);
  list.innerHTML = recent.length
    ? recent.map(exerciseLink).join("")
    : "<p>No exercises published yet.</p>";
}

main().catch((error) => {
  console.error(error);
  document.querySelector("#exercise-list").innerHTML =
    `<p>Failed to load SardineTrace data: ${escapeHtml(error.message)}</p>`;
});
