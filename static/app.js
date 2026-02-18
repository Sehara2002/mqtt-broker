const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

const clientsEl = document.getElementById("clients");
const publishesEl = document.getElementById("publishes");
const msgRateEl = document.getElementById("msgRate");
const uptimeEl = document.getElementById("uptime");
const eventsTable = document.getElementById("eventsTable");

function setStatus(ok, text) {
  statusDot.className = ok ? "dot ok" : "dot bad";
  statusText.textContent = text;
}

function nowTime() {
  return new Date().toLocaleTimeString();
}

function pushRow(data, rate) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${nowTime()}</td>
    <td>${data.clients ?? 0}</td>
    <td>${data.publishes_total ?? 0}</td>
    <td>${rate.toFixed(2)}</td>
    <td>${data.bytes_in_total ?? 0}</td>
    <td>${data.bytes_out_total ?? 0}</td>
  `;
  eventsTable.prepend(tr);
  while (eventsTable.children.length > 25) {
    eventsTable.removeChild(eventsTable.lastChild);
  }
}

// Charts
const rateCtx = document.getElementById("rateChart").getContext("2d");
const clientsCtx = document.getElementById("clientsChart").getContext("2d");

let labels = [];
let rateSeries = [];
let clientsSeries = [];

const rateChart = new Chart(rateCtx, {
  type: "line",
  data: {
    labels,
    datasets: [{ label: "publishes/sec", data: rateSeries, tension: 0.25, fill: false }]
  },
  options: { animation: false, responsive: true, scales: { y: { beginAtZero: true } } }
});

const clientsChart = new Chart(clientsCtx, {
  type: "line",
  data: {
    labels,
    datasets: [{ label: "clients", data: clientsSeries, tension: 0.25, fill: false }]
  },
  options: { animation: false, responsive: true, scales: { y: { beginAtZero: true } } }
});

// Compute publishes/sec from publishes_total delta
let lastPublishes = null;
let lastTs = null;

function computeRate(publishesTotal) {
  const now = Date.now();
  if (lastPublishes === null) {
    lastPublishes = publishesTotal;
    lastTs = now;
    return 0;
  }
  const dp = publishesTotal - lastPublishes;
  const dt = (now - lastTs) / 1000.0;
  lastPublishes = publishesTotal;
  lastTs = now;
  if (dt <= 0) return 0;
  return dp / dt;
}

function pushPoint(rate, clients) {
  labels.push(nowTime());
  rateSeries.push(rate);
  clientsSeries.push(clients);

  if (labels.length > 60) {
    labels.shift();
    rateSeries.shift();
    clientsSeries.shift();
  }

  rateChart.update();
  clientsChart.update();
}

let es = null;

function connectSSE() {
  setStatus(false, "Connecting…");
  if (es) es.close();

  es = new EventSource("/events");

  es.onopen = () => setStatus(true, "Live");
  es.onerror = () => {
    setStatus(false, "Disconnected — retrying…");
    try { es.close(); } catch {}
    setTimeout(connectSSE, 1500);
  };

  es.onmessage = (evt) => {
    const data = JSON.parse(evt.data);

    const publishesTotal = data.publishes_total ?? 0;
    const rate = computeRate(publishesTotal);
    const clients = data.clients ?? 0;

    clientsEl.textContent = clients;
    publishesEl.textContent = publishesTotal;
    msgRateEl.textContent = rate.toFixed(2);
    uptimeEl.textContent = (data.uptime_sec ?? 0);

    pushPoint(rate, clients);
    pushRow(data, rate);
  };
}

connectSSE();
