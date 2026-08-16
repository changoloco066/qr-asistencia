const params = new URLSearchParams(window.location.search);
const sessionId = params.get("session");
const token = params.get("token");

const form = document.getElementById("checkin-form");
const resultMsg = document.getElementById("result-msg");

if (!sessionId || !token) {
  resultMsg.textContent = "Este enlace no es válido. Escanea el código QR de la clase.";
  form.style.display = "none";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const matricula = document.getElementById("matricula").value.trim();

  resultMsg.textContent = "Registrando...";

  try {
    const res = await fetch("/api/checkin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: Number(sessionId), token, matricula }),
    });
    const data = await res.json();

    if (res.ok) {
      resultMsg.textContent = `Listo, ${data.full_name}. Asistencia registrada.`;
      form.style.display = "none";
      return;
    }

    const messages = {
      expired_or_invalid_token: "El código ya expiró, pídele a tu profesora que lo actualice y escanea de nuevo.",
      matricula_not_found: "Esa matrícula no está en la lista de la clase.",
      already_checked_in: "Ya habías pasado asistencia en esta clase.",
      missing_fields: "Falta tu matrícula.",
    };
    resultMsg.textContent = messages[data.error] || "Algo salió mal, intenta de nuevo.";
  } catch (err) {
    resultMsg.textContent = "No se pudo conectar con el servidor.";
  }
});