const token = localStorage.getItem("token");
if (!token) {
  window.location.href = "login.html";
}

const authHeaders = { Authorization: `Bearer ${token}` };

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "login.html";
});

async function loadRoster() {
  const res = await fetch("/api/roster", { headers: authHeaders });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "login.html";
    return;
  }
  const students = await res.json();
  renderRoster(students);
}

function renderRoster(students) {
  const tbody = document.querySelector("#roster-table tbody");
  tbody.innerHTML = "";
  document.getElementById("student-count").textContent = students.length;

  for (const s of students) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${s.matricula}</td>
      <td>${s.full_name}</td>
      <td><button class="delete-btn" data-matricula="${s.matricula}">Eliminar</button></td>
    `;
    tbody.appendChild(tr);
  }

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/roster/${btn.dataset.matricula}`, {
        method: "DELETE",
        headers: authHeaders,
      });
      loadRoster();
    });
  });
}

document.getElementById("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const matricula = document.getElementById("matricula").value.trim();
  const full_name = document.getElementById("full-name").value.trim();

  await fetch("/api/roster", {
    method: "POST",
    headers: { ...authHeaders, "Content-Type": "application/json" },
    body: JSON.stringify({ matricula, full_name }),
  });

  e.target.reset();
  loadRoster();
});

document.getElementById("upload-btn").addEventListener("click", async () => {
  const fileInput = document.getElementById("csv-input");
  const msg = document.getElementById("upload-msg");

  if (!fileInput.files.length) {
    msg.textContent = "Selecciona un archivo CSV primero.";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch("/api/roster/bulk", {
    method: "POST",
    headers: authHeaders,
    body: formData,
  });

  const data = await res.json();
  msg.textContent = res.ok
    ? `Se importaron ${data.imported} alumnos.`
    : "Hubo un error al subir el archivo.";

  loadRoster();
});

loadRoster();
