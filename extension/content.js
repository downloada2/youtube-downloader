// Плавающая панель «MP3 / MP4» на страницах видео YouTube (Shadow DOM, чтобы стили сайта не мешали).
(() => {
  const host = document.createElement("div");
  host.style.cssText = "position:fixed;right:18px;bottom:18px;z-index:2147483647;display:none";
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `
  <style>
    .bar{display:flex;gap:6px;align-items:center;padding:6px;border-radius:999px;
      background:rgba(18,14,36,.82);backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,.14);
      box-shadow:0 10px 30px rgba(0,0,0,.45);font:600 13px/1 system-ui,Segoe UI,sans-serif;color:#fff}
    button{all:unset;cursor:pointer;padding:10px 16px;border-radius:999px;color:#fff;letter-spacing:.2px}
    .a{background:linear-gradient(135deg,#6366f1,#a855f7 60%,#ec4899)}
    .v{background:linear-gradient(135deg,#f43f5e,#fb923c)}
    button:hover{filter:brightness(1.12)}
    button:active{transform:scale(.97)}
    .msg{padding:0 12px 0 6px;font-weight:500;opacity:.9;max-width:240px}
    .hide{display:none}
  </style>
  <div class="bar">
    <button class="a" data-m="audio">⬇ MP3</button>
    <button class="v" data-m="video">⬇ MP4</button>
    <span class="msg hide"></span>
  </div>`;
  document.documentElement.appendChild(host);
  const msg = root.querySelector(".msg");
  let timer;
  const say = (t) => { msg.textContent = t; msg.classList.remove("hide"); clearTimeout(timer); timer = setTimeout(() => msg.classList.add("hide"), 5000); };

  root.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "download", url: location.href, mode: b.dataset.m }, (r) => {
      if (!r || r.error === "offline") say("Запустите программу YouTube Downloader");
      else if (r.error === "busy") say("Программа занята другой загрузкой");
      else if (r.ok) say("Отправлено в программу ✓");
      else say("Не получилось");
    });
  }));

  const isVideo = () => /^\/(watch|shorts\/)/.test(location.pathname);
  const sync = () => { host.style.display = isVideo() ? "block" : "none"; };
  sync();
  setInterval(sync, 800); // YouTube — SPA, адрес меняется без перезагрузки
})();
