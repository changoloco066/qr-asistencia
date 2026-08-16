const token = localStorage.getItem("token");
if (!token) {
  window.location.href = "login.html";
}
const authHeaders = { Authorization: `Bearer ${token}` };

const TOKEN_ROTATE_MS = 20000; // rotate QR before the backend's 25s window closes
const STATUS_POLL_MS = 4000;
const COUNTDOWN_SECONDS = TOKEN_ROTATE_MS / 1000;

let sessionId = null;
let qrRenderer = null;
let secondsLeft = COUNTDOWN_SECONDS;

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

async function startSession() {
  const res = await fetch("/api/sessions/start", {
    method: "POST",
    headers: authHeaders,
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return;
  }
  const data = await res.json();
  sessionId = data.session_id;
}

async function rotateQr() {
  if (!sessionId) return;

  const res = await fetch(`/api/sessions/${sessionId}/token`, {
    method: "POST",
    headers: authHeaders,
  });
  const data = await res.json();

  const checkinUrl = `${window.location.origin}/checkin.html?session=${sessionId}&token=${data.token}`;

  const container = document.getElementById("qrcode");
  container.innerHTML = "";
  qrRenderer = new QRCode(container, {
    text: checkinUrl,
    width: 220,
    height: 220,
  });

  secondsLeft = COUNTDOWN_SECONDS;
  updateCountdownDisplay();
}

function updateCountdownDisplay() {
  document.getElementById("countdown").textContent = secondsLeft;
}

function tickCountdown() {
  secondsLeft = Math.max(0, secondsLeft - 1);
  updateCountdownDisplay();
}

async function pollStatus() {
  if (!sessionId) return;

  const res = await fetch(`/api/sessions/${sessionId}/status`, {
    headers: authHeaders,
  });
  const data = await res.json();

  document.getElementById("checked-count").textContent = data.checked_in_count;
  document.getElementById("total-count").textContent = data.total_roster;

  const tbody = document.querySelector("#status-table tbody");
  tbody.innerHTML = "";
  for (const row of data.checked_in) {
    const tr = document.createElement("tr");
    const time = new Date(row.checked_in_at).toLocaleTimeString("es-MX", {
      hour: "2-digit",
      minute: "2-digit",
    });
    tr.innerHTML = `<td>${row.matricula}</td><td>${row.full_name}</td><td>${time}</td>`;
    tbody.appendChild(tr);
  }
}

async function init() {
  await startSession();
  await rotateQr();
  await pollStatus();

  setInterval(rotateQr, TOKEN_ROTATE_MS);
  setInterval(pollStatus, STATUS_POLL_MS);
  setInterval(tickCountdown, 1000);
}

init();