// Makes ui/index.html (written for pywebview) work in a normal browser: window.pywebview.api -> fetch().
(() => {
  let sid = localStorage.getItem("ytdl_sid");
  if (!/^[0-9a-f]{32}$/.test(sid || "")) {
    sid = [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
    localStorage.setItem("ytdl_sid", sid);
  }
  const call = (name) => async (...args) => {
    const r = await fetch("/api/" + name, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Sid": sid }, body: JSON.stringify({ args }),
    });
    return r.json();
  };
  const save = (url) => { const a = document.createElement("a"); a.href = url; a.download = ""; document.body.appendChild(a); a.click(); a.remove(); };
  window.pywebview = {
    api: {
      get_state: call("get_state"), set_theme: call("set_theme"), set_mode: call("set_mode"),
      start: call("start"), cancel: call("cancel"), poll: call("poll"), clear_history: call("clear_history"),
      paste: async () => { try { return (await navigator.clipboard.readText()).trim(); } catch (e) { return ""; } },
      pick_folder: async () => null, open_folder: async () => {}, exit_app: async () => {},
      reveal: async (p) => save(p), open_file: async (p) => save(p),
    },
  };
  document.addEventListener("DOMContentLoaded", () => {
    const hide = (el) => el && (el.style.display = "none");
    const out = document.getElementById("outdir");
    hide(out && out.parentElement.parentElement);              // "Папка сохранения"
    hide(document.getElementById("btnOpenDir"));
    hide(document.getElementById("plRow"));                    // плейлисты только в приложении
    document.querySelectorAll(".hist-head .btn-sm").forEach(hide);
    window.dispatchEvent(new Event("pywebviewready"));
  });
})();
