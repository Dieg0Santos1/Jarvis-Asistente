window.jarvisUi = {
  setState(state) {
    document.body.dataset.state = state;
    const label = document.querySelector(".state-label");
    if (label) {
      label.textContent = String(state).toUpperCase();
    }
  },
};
