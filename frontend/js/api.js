// ===== GENAI EDUCANTION ENGINE API Wrapper =====
const API = {
  base: "",  // same origin (Flask serves both)

  async request(method, endpoint, body = null) {
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(this.base + endpoint, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, message: data.error || "Request failed", ...data };
    return data;
  },

  get:    (ep)       => API.request("GET", ep),
  post:   (ep, body) => API.request("POST", ep, body),
  put:    (ep, body) => API.request("PUT", ep, body),
  delete: (ep)       => API.request("DELETE", ep),
};

// Auth helpers
const Auth = {
  async me() {
    try { return await API.get("/api/auth/me"); }
    catch { return null; }
  },
  async requireAuth() {
    const user = await this.me();
    if (!user) { window.location.href = "/login.html"; return null; }
    return user;
  },
  async logout() {
    await API.post("/api/auth/logout");
    window.location.href = "/login.html";
  }
};

// Toast notification
function showToast(message, type = "info") {
  let toast = document.getElementById("global-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "global-toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  const icons  = { info: "info", success: "check_circle", error: "error", warning: "warning" };
  const colors = { info: "#60a5fa", success: "#34d399", error: "#f87171", warning: "#fbbf24" };
  toast.innerHTML = `
    <span class="material-symbols-outlined" style="color:${colors[type]};font-size:1.25rem">${icons[type]}</span>
    <span style="font-size:0.875rem;font-weight:500">${message}</span>
  `;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3500);
}

// Sidebar active state
function setActiveSidebarItem(page) {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });
}

// Mobile sidebar toggle
function initMobileSidebar() {
  const btn     = document.getElementById("menu-btn");
  const sidebar = document.querySelector(".sidebar");
  if (btn && sidebar) {
    // Add overlay if it doesn't exist
    let overlay = document.querySelector(".sidebar-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "sidebar-overlay";
      sidebar.after(overlay);
    }

    const toggle = () => {
      const isOpen = sidebar.classList.toggle("open");
      document.body.style.overflow = isOpen ? "hidden" : "";
    };

    btn.addEventListener("click", e => { e.stopPropagation(); toggle(); });
    overlay.addEventListener("click", toggle);
    
    // Close on nav link click (for mobile)
    sidebar.querySelectorAll(".nav-item").forEach(item => {
      item.addEventListener("click", () => {
        if (window.innerWidth <= 768) {
          sidebar.classList.remove("open");
          document.body.style.overflow = "";
        }
      });
    });
  }
}

// Color map for courses
const COURSE_COLORS = {
  blue:    { bg: "rgba(59,130,246,0.12)",  text: "#60a5fa",  border: "rgba(59,130,246,0.3)" },
  violet:  { bg: "rgba(139,92,246,0.12)",  text: "#a78bfa",  border: "rgba(139,92,246,0.3)" },
  emerald: { bg: "rgba(16,185,129,0.12)",  text: "#34d399",  border: "rgba(16,185,129,0.3)" },
  orange:  { bg: "rgba(245,158,11,0.12)",  text: "#fbbf24",  border: "rgba(245,158,11,0.3)" },
  amber:   { bg: "rgba(251,191,36,0.12)",  text: "#fde68a",  border: "rgba(251,191,36,0.3)" },
  teal:    { bg: "rgba(20,184,166,0.12)",  text: "#2dd4bf",  border: "rgba(20,184,166,0.3)" },
};
function courseColor(color) { return COURSE_COLORS[color] || COURSE_COLORS.blue; }

// User header display
async function populateUserHeader() {
  const user = await Auth.me();
  if (!user) return;
  const nameEl = document.getElementById("user-display-name");
  const xpEl   = document.getElementById("user-xp");
  const lvlEl  = document.getElementById("user-level");
  if (nameEl) nameEl.textContent = user.name;
  if (xpEl)   xpEl.textContent   = user.xp?.toLocaleString() + " XP";
  if (lvlEl)  lvlEl.textContent  = user.level;

  // Logout buttons
  document.querySelectorAll("[data-action='logout']").forEach(btn => {
    btn.addEventListener("click", () => Auth.logout());
  });
}

// ===== XP System with Level-Up Animation =====
const XP = {
  _levelThresholds: [0,100,250,500,1000,2000,3500,5000,7500,10000],
  _levelNames: [
    "Beginner I","Beginner II","Apprentice","Student","Scholar",
    "Expert","Master","Grandmaster","Legend","Elite"
  ],

  levelFor(xp) {
    for (let i = this._levelThresholds.length - 1; i >= 0; i--) {
      if (xp >= this._levelThresholds[i]) return i;
    }
    return 0;
  },

  /** Call this after any XP-earning action. oldXp optional — if provided, detects level-up. */
  async gain(amount, msg = '', oldXp = null) {
    // Show floating XP popup
    this.showPopup(amount, msg);

    // If we have old XP, check for level-up
    if (oldXp !== null) {
      const user = await Auth.me().catch(() => null);
      if (user) {
        const newLevel = this.levelFor(user.xp);
        const oldLevel = this.levelFor(oldXp);
        if (newLevel > oldLevel) {
          setTimeout(() => this.showLevelUp(this._levelNames[newLevel] || `Level ${newLevel}`), 800);
        }
        // Animate XP bar if present
        this._animateBar(oldXp, user.xp);
        // Update header XP badge
        const xpEl = document.getElementById("user-xp");
        if (xpEl) xpEl.textContent = user.xp.toLocaleString() + " XP";
      }
    }
  },

  showPopup(amount, msg) {
    const popup = document.createElement("div");
    popup.className = "xp-popup";
    popup.innerHTML = `
      <span class="material-symbols-outlined" style="font-size:1.5rem;color:#fbbf24">bolt</span>
      <div>
        <div style="font-size:1rem;font-weight:900">+${amount} XP!</div>
        <div style="font-size:.75rem;opacity:.85">${msg || 'Keep it up!'}</div>
      </div>`;
    document.body.appendChild(popup);
    requestAnimationFrame(() => popup.classList.add("visible"));
    setTimeout(() => { popup.classList.add("hide"); setTimeout(() => popup.remove(), 400); }, 3000);
  },

  showLevelUp(levelName) {
    // Create a full-screen level-up overlay
    const overlay = document.createElement("div");
    overlay.id = "level-up-overlay";
    overlay.style.cssText = `
      position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;
      background:rgba(0,0,0,.75);backdrop-filter:blur(8px);animation:fadeIn .3s ease`;
    overlay.innerHTML = `
      <div style="text-align:center;animation:zoomIn .5s cubic-bezier(.34,1.56,.64,1)">
        <div style="font-size:5rem;margin-bottom:.5rem;animation:spin1 .6s ease">⭐</div>
        <div style="font-size:.9rem;font-weight:700;color:#fbbf24;text-transform:uppercase;letter-spacing:.12em;margin-bottom:.5rem">Level Up!</div>
        <div style="font-size:2.5rem;font-weight:900;background:linear-gradient(135deg,#fbbf24,#f87171,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:1rem">${levelName}</div>
        <p style="color:#94a3b8;font-size:.9rem;margin-bottom:1.5rem">You've reached a new milestone. Keep pushing!</p>
        <button onclick="document.getElementById('level-up-overlay').remove()" style="padding:.65rem 2rem;border-radius:var(--radius-full);background:linear-gradient(135deg,#4746E5,#8b5cf6);color:#fff;border:none;font-weight:700;cursor:pointer;font-size:.9rem">Awesome! 🎉</button>
      </div>`;
    // Inject keyframes if not already present
    if (!document.getElementById("xp-keyframes")) {
      const style = document.createElement("style");
      style.id = "xp-keyframes";
      style.textContent = `
        @keyframes zoomIn{from{opacity:0;transform:scale(.6)}to{opacity:1;transform:scale(1)}}
        @keyframes fadeIn{from{opacity:0}to{opacity:1}}
        @keyframes spin1{0%{transform:rotate(0)}100%{transform:rotate(360deg)}}
        .xp-popup{position:fixed;bottom:5.5rem;right:1.5rem;z-index:8000;display:flex;align-items:center;gap:.75rem;padding:.85rem 1.25rem;background:rgba(30,30,50,.95);border:1px solid rgba(251,191,36,.4);border-radius:var(--radius-xl);box-shadow:0 8px 32px rgba(0,0,0,.4);backdrop-filter:blur(12px);opacity:0;transform:translateY(16px);transition:all .35s cubic-bezier(.34,1.56,.64,1);pointer-events:none}
        .xp-popup.visible{opacity:1;transform:translateY(0)}
        .xp-popup.hide{opacity:0;transform:translateY(-12px)}`;
      document.head.appendChild(style);
    }
    document.body.appendChild(overlay);
    overlay.addEventListener("click", e => { if (e.target === overlay) overlay.remove(); });
    setTimeout(() => overlay.remove(), 6000);
  },

  _animateBar(fromXp, toXp) {
    const bar = document.getElementById("xp-progress-bar");
    if (!bar) return;
    const lvl = this.levelFor(fromXp);
    const lo  = this._levelThresholds[lvl]     || 0;
    const hi  = this._levelThresholds[lvl + 1] || lo + 500;
    const pct = Math.min(100, ((toXp - lo) / (hi - lo)) * 100);
    bar.style.width = pct + "%";
  }
};
// ===== GENAI EDUCANTION ENGINE Streaming Helper =====
window.Streaming = class Streaming {
  static async consume(response, { onToken, onDone, onError }) {
    if (!response.ok) {
      if (onError) onError(new Error(`Server returned ${response.status}`));
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let lines = buffer.split("\n");
        buffer = lines.pop();
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const dataStr = trimmed.substring(6).trim();
          if (dataStr === "[DONE]") { if (onDone) onDone(); return; }
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.token && onToken) onToken(parsed.token);
            else if (parsed.error && onError) onError(new Error(parsed.error));
          } catch (e) { console.warn("Stream JSON parse error:", e, dataStr); }
        }
      }
      if (onDone) onDone();
    } catch (err) { if (onError) onError(err); }
    finally { reader.releaseLock(); }
  }

  static parseJSON(text) {
    try {
      const match = text.match(/(\[[\s\S]*\]|\{[\s\S]*\})/);
      const target = match ? match[0] : text;
      try { return JSON.parse(target); }
      catch (e) { return JSON.parse(this.repairJSON(target)); }
    } catch (e) { throw e; }
  }

  static repairJSON(json) {
    let stack = [];
    let inString = false;
    let escaped = false;
    for (let i = 0; i < json.length; i++) {
      const char = json[i];
      if (escaped) { escaped = false; continue; }
      if (char === '\\') { escaped = true; continue; }
      if (char === '"') { inString = !inString; continue; }
      if (inString) continue;
      if (char === '[' || char === '{') stack.push(char === '[' ? ']' : '}');
      else if (char === ']' || char === '}') {
        if (stack.length > 0 && stack[stack.length - 1] === char) stack.pop();
      }
    }
    let repaired = json;
    if (inString) repaired += '"';
    while (stack.length > 0) repaired += stack.pop();
    return repaired;
  }
};
console.log("🚀 GENAI EDUCANTION ENGINE: Core API & Streaming Helper Loaded");
