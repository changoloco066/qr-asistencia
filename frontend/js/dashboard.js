const token = localStorage.getItem("token");
if (!token) {
  window.location.href = "login.html";
}
const authHeaders = { Authorization: `Bearer ${token}` };

const TOKEN_ROTATE_MS = 40000; // rotate QR before the backend's 45s window closes
const STATUS_POLL_MS = 4000;
const COUNTDOWN_SECONDS = TOKEN_ROTATE_MS / 1000;

let sessionId = null;
let secondsLeft = COUNTDOWN_SECONDS;
let rotateInterval = null;
let pollInterval = null;
let countdownInterval = null;

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

document.getElementById("start-btn").addEventListener("click", startClass);
document.getElementById("finish-btn").addEventListener("click", finishClass);
document.getElementById("cancel-btn").addEventListener("click", cancelClass);
document.getElementById("reopen-btn").addEventListener("click", reopenClass);

function showPanel(name) {
  document.getElementById("start-panel").classList.toggle("hidden", name !== "start");
  document.getElementById("active-panel").classList.toggle("hidden", name !== "active");
  document.getElementById("finished-panel").classList.toggle("hidden", name !== "finished");
  document.getElementById("danger-zone").classList.toggle("hidden", name === "start");
}

function stopLiveUpdates() {
  clearInterval(rotateInterval);
  clearInterval(pollInterval);
  clearInterval(countdownInterval);
}

async function startClass() {
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

  showPanel("active");
  await goLive();
}

async function goLive() {
  showPanel("active");
  await rotateQr();
  await pollStatus();

  rotateInterval = setInterval(rotateQr, TOKEN_ROTATE_MS);
  pollInterval = setInterval(pollStatus, STATUS_POLL_MS);
  countdownInterval = setInterval(tickCountdown, 1000);
}

async function finishClass() {
  if (!sessionId) return;
  stopLiveUpdates();

  await fetch(`/api/sessions/${sessionId}/finish`, {
    method: "POST",
    headers: authHeaders,
  });

  await showFinishedSummary();
}

async function showFinishedSummary() {
  const res = await fetch(`/api/sessions/${sessionId}/status`, {
    headers: authHeaders,
  });
  const data = await res.json();
  document.getElementById("finished-count").textContent = data.checked_in_count;
  showPanel("finished");
}

async function reopenClass() {
  if (!sessionId) return;

  await fetch(`/api/sessions/${sessionId}/reopen`, {
    method: "POST",
    headers: authHeaders,
  });

  await goLive();
}

async function cancelClass() {
  if (!confirm("¿Cancelar la clase de hoy? Se borrará cualquier asistencia ya registrada hoy.")) {
    return;
  }

  stopLiveUpdates();

  await fetch("/api/sessions/today", {
    method: "DELETE",
    headers: authHeaders,
  });

  sessionId = null;
  showPanel("start");
}

async function rotateQr() {
  if (!sessionId) return;

  const res = await fetch(`/api/sessions/${sessionId}/token`, {
    method: "POST",
    headers: authHeaders,
  });
  const data = await res.json();

  if (!res.ok) {
    // e.g. session got finished from elsewhere -- stop trying to rotate
    stopLiveUpdates();
    return;
  }

  const checkinUrl = `${window.location.origin}/checkin.html?session=${sessionId}&token=${data.token}`;

  const container = document.getElementById("qrcode");
  container.innerHTML = "";
  new QRCode(container, {
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

// On load: read-only check of today's session. Three possible states --
// no session (show start button), active session (resume live QR), or
// finished session (show the closed summary). Nothing is created here.
async function init() {
  const res = await fetch("/api/sessions/today", { headers: authHeaders });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return;
  }
  const data = await res.json();

  if (!data.exists) {
    showPanel("start");
    return;
  }

  sessionId = data.session_id;

  if (data.finished) {
    await showFinishedSummary();
  } else {
    await goLive();
  }
}

init();