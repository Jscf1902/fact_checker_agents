// script.js (reemplazar todo el archivo con esto)
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("user-input");
  const button = document.getElementById("send-btn");
  const messages = document.getElementById("messages");
  const loader = document.getElementById("loader");

  // Si hay un form ancestro, prevenir su submit por defecto.
  const form = input ? input.closest("form") : null;
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
    });
  }

  function appendMessage(text, className) {
    const div = document.createElement("div");
    div.className = "message " + className;

    // Permitir saltos de línea: insertar como texto con reemplazo de \n por <br>
    // Usamos innerHTML solo para convertir saltos de línea en <br> (textContent evita XSS)
    const safeText = String(text || "");
    const withBreaks = safeText
      .split("\n")
      .map(line => line.replace(/</g, "&lt;").replace(/>/g, "&gt;"))
      .join("<br>");
    div.innerHTML = withBreaks;

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  let isProcessing = false;

  async function sendMessage(e) {
    if (e && typeof e.preventDefault === "function") e.preventDefault();

    // Evitar múltiples envíos
    if (isProcessing) return;
    const text = input.value.trim();
    if (!text) return;

    appendMessage(text, "user-message");

    // bloquear UI
    input.value = "";
    input.disabled = true;
    button.disabled = true;
    loader.style.display = "block";
    isProcessing = true;

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // IMPORTANTE: usar la clave 'message' ya que así la espera tu web_app
        body: JSON.stringify({ message: text }),
      });

      // manejar errores HTTP
      if (!resp.ok) {
        let errText = `Error ${resp.status}`;
        try {
          const errJson = await resp.json();
          if (errJson && errJson.error) errText += ` — ${errJson.error}`;
        } catch (_) {}
        appendMessage(`❌ Error del servidor: ${errText}`, "bot-message");
      } else {
        const data = await resp.json();
        // tu web_app responde {"response": "..."} o {"error":"..."}
        if (data.response) {
          appendMessage(data.response, "bot-message");
        } else if (data.error) {
          appendMessage(`❌ ${data.error}`, "bot-message");
        } else {
          // fallback: stringify whole body
          appendMessage(JSON.stringify(data), "bot-message");
        }
      }
    } catch (err) {
      console.error("Error en fetch /api/chat:", err);
      appendMessage("❌ Error conectando con el servidor.", "bot-message");
    } finally {
      loader.style.display = "none";
      input.disabled = false;
      button.disabled = false;
      input.focus();
      isProcessing = false;
    }
  }

  // click en botón
  if (button) button.addEventListener("click", sendMessage);

  // Enter en input
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(e);
      }
    });
  }
});
