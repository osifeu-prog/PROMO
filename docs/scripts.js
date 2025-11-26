document.addEventListener("DOMContentLoaded", () => {
  const tempoLabel = document.getElementById("tempo-label");
  if (!tempoLabel) return;

  const modes = ["Calm", "Focus", "Aggressive"];
  let idx = 0;

  tempoLabel.parentElement.addEventListener("click", () => {
    idx = (idx + 1) % modes.length;
    tempoLabel.textContent = modes[idx];
  });
});
