const token = localStorage.getItem("token");
if (!token) {
  window.location.href = "login.html";
}
const authHeaders = { Authorization: `Bearer ${token}` };

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

async function loadSummary() {
  const res = await fetch("/api/stats/summary", { headers: authHeaders });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return;
  }
  const data = await res.json();
  document.getElementById("summary-sessions").textContent = data.total_sessions;
  document.getElementById("summary-students").textContent = data.total_students;
  document.getElementById("summary-avg").textContent = `${data.average_attendance_pct}%`;
}

async function loadStudentStats() {
  const res = await fetch("/api/stats/students", { headers: authHeaders });
  const students = await res.json();

  const tbody = document.querySelector("#stats-table tbody");
  tbody.innerHTML = "";

  for (const s of students) {
    const tr = document.createElement("tr");
    tr.className = s.at_risk ? "at-risk" : "";
    tr.style.cursor = "pointer";
    tr.innerHTML = `
      <td>${s.matricula}</td>
      <td>${s.full_name}</td>
      <td>${s.attended} / ${s.total_sessions}</td>
      <td>${s.absences}</td>
      <td>${s.attendance_pct}%</td>
    `;
    tr.addEventListener("click", () => loadDetail(s.matricula, s.full_name));
    tbody.appendChild(tr);
  }
}

async function loadDetail(matricula, fullName) {
  const res = await fetch(`/api/stats/students/${matricula}`, {
    headers: authHeaders,
  });
  const data = await res.json();

  document.getElementById("detail-card").classList.remove("hidden");
  document.getElementById("detail-name").textContent = `${fullName} (${matricula})`;

  const tbody = document.querySelector("#detail-table tbody");
  tbody.innerHTML = "";
  for (const s of data.sessions) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.session_date}</td>
      <td>${s.attended ? "✅ Presente" : "❌ Falta"}</td>
    `;
    tbody.appendChild(tr);
  }

  document.getElementById("detail-card").scrollIntoView({ behavior: "smooth" });
}

loadSummary();
loadStudentStats();