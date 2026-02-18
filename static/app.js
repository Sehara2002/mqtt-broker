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

function pushRow(data) {
  const tr = document.createElement("tr");
  tr.innerHTML = `
    <td>${nowTime()}</td>
    <td>${data.clients}</td>
    <td>${data.publishes_total}</td>
    <td>${data.msg_rate}</td>
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
    datasets: [{
      label: "msg/sec",
      data: rateSeries,
      tension: 0.25,
      fill: false
    }]
  },
  options: { animation: false, responsive: true, scales: { y: { beginAtZero: true } } }
});

const clientsChart = new Chart(clientsCtx, {
  type: "line",
  data: {
    labels,
    datasets: [{
      label: "clients",
      data: clientsSeries,
      tension: 0.25,
      fill: false
    }]
  },
  options: { animation: false, responsive: true, scales: { y: { beginAtZero: true } } }
});

function pushPoint(data) {
  labels.push(nowTime());
  rateSeries.push(data.msg_rate);
  clientsSeries.push(data.clients);

  if (labels.length > 60) {
    labels.shift();
    rateSeries.shift();
    clientsSeries.shift();
  }

  rateChart.update();
  clientsChart.update();
}

// Live stream (SSE)
let es = null;

function connectSSE() {
  setStatus(false, "Connecting…");
  if (es) es.close();

  es = new EventSource("/events");

  es.onopen = () => setStatus(true, "Live");
  es.onerror = () => {
    setStatus(false, "Disconnected - retrying…");
    try { es.close(); } catch {}
    setTimeout(connectSSE, 1500);
  };

  es.onmessage = (evt) => {
    const data = JSON.parse(evt.data);

    clientsEl.textContent = data.clients;
    publishesEl.textContent = data.publishes_total;
    msgRateEl.textContent = data.msg_rate;
    uptimeEl.textContent = data.uptime_sec;

    pushPoint(data);
    pushRow(data);
  };
}

connectSSE();
