const form = document.getElementById("login-form");
const errorMsg = document.getElementById("error-msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorMsg.classList.add("hidden");

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      errorMsg.textContent = "Usuario o contraseña incorrectos.";
      errorMsg.classList.remove("hidden");
      return;
    }

    localStorage.setItem("token", data.token);
    window.location.href = "roster.html";
  } catch (err) {
    errorMsg.textContent = "No se pudo conectar con el servidor.";
    errorMsg.classList.remove("hidden");
  }
});
