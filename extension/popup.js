const $ = (s) => document.querySelector(s);
const state = $("#state"), st = $("#st");

chrome.runtime.sendMessage({ type: "ping" }, (r) => {
  if (r && r.ok) { state.textContent = "Программа запущена ✓"; state.className = "ok"; }
  else { state.textContent = "Программа не запущена — откройте YouTube Downloader"; state.className = "bad"; }
});

document.querySelectorAll("button").forEach((b) => b.addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab && tab.url || "";
  if (!/^https:\/\/(www\.|m\.)?youtube\.com\/|^https:\/\/youtu\.be\//.test(url)) {
    st.textContent = "Откройте страницу видео на YouTube"; st.className = "bad"; return;
  }
  chrome.runtime.sendMessage({ type: "download", url, mode: b.dataset.m }, (r) => {
    if (!r || r.error === "offline") { st.textContent = "Программа не запущена"; st.className = "bad"; }
    else if (r.error === "busy") { st.textContent = "Занята другой загрузкой"; st.className = "bad"; }
    else if (r.ok) { st.textContent = "Отправлено в программу ✓"; st.className = "ok"; }
    else { st.textContent = "Не получилось"; st.className = "bad"; }
  });
}));
