window.jarvisUi = {
  setState(state) {
    document.body.dataset.state = state;
    const label = document.querySelector(".state-label");
    if (label) {
      label.textContent = String(state).toUpperCase();
    }

    const kicker = document.querySelector(".detail-kicker");
    if (kicker) {
      kicker.textContent = stateLabel(state);
    }
  },
  setDetail(text) {
    const detail = document.querySelector(".detail-text");
    if (detail) {
      const safeText = compactDetail(text || "En espera");
      detail.textContent = safeText;
      detail.title = text || "";
      detail.scrollTop = 0;
    }
  },
  setCameraPreview(imageDataUrl, label = "VISION FEED") {
    const image = document.querySelector(".camera-preview-image");
    const labelNode = document.querySelector(".camera-preview-label");
    if (!image) {
      return;
    }

    image.src = imageDataUrl || "";
    if (labelNode) {
      labelNode.textContent = label;
    }
    document.body.dataset.preview = imageDataUrl ? "camera" : "none";
  },
  clearCameraPreview() {
    const image = document.querySelector(".camera-preview-image");
    if (image) {
      image.removeAttribute("src");
    }
    document.body.dataset.preview = "none";
  },
  setSecurityStatus(state = "unknown", label = "SIN IDENTIFICAR") {
    document.body.dataset.security = state;
    const badge = document.querySelector(".security-badge");
    if (badge) {
      badge.textContent = label;
    }
  },
};

function stateLabel(state) {
  const labels = {
    idle: "Sistema en espera",
    listening: "Canal de voz abierto",
    thinking: "Procesamiento neural",
    speaking: "Respuesta en curso",
  };
  return labels[state] || "Sistema de voz";
}

function compactDetail(text) {
  const cleaned = String(text).replace(/\s+/g, " ").trim();
  const maxLength = 420;
  if (cleaned.length <= maxLength) {
    return cleaned;
  }
  return `${cleaned.slice(0, maxLength - 1).trim()}...`;
}
