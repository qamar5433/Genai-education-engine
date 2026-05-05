

/* ── XP & Level-Up Manager ── */
const XP = {
  showGain(amount, msg = '') {
    const popup = document.createElement('div');
    popup.className = 'xp-popup';
    popup.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:1.5rem">bolt</span>
      <div>
        <div style="font-size:1rem;font-weight:900">+${amount} XP!</div>
        <div style="font-size:.75rem;opacity:.85">${msg || 'Keep it up!'}</div>
      </div>`;
    document.body.appendChild(popup);
    setTimeout(() => { popup.classList.add('hide'); setTimeout(() => popup.remove(), 400); }, 3000);
  }
};

/* ── Streak Heatmap Builder ── */
const Heatmap = {
  build(containerId, activityData = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const weeks = 26; // ~6 months
    const today = new Date();
    const cells = [];

    for (let w = weeks - 1; w >= 0; w--) {
      const col = document.createElement('div');
      col.className = 'heatmap-col';
      for (let d = 0; d < 7; d++) {
        const date = new Date(today);
        date.setDate(today.getDate() - (w * 7 + (6 - d)));
        const key = date.toISOString().slice(0, 10);
        const count = activityData[key] || 0;
        const cell = document.createElement('div');
        cell.className = 'heatmap-cell' + (count > 0 ? ` lvl-${Math.min(4, count)}` : '');
        cell.title = `${key}: ${count} activities`;
        col.appendChild(cell);
      }
      container.appendChild(col);
    }
  }
};


