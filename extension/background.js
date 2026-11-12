const BASE = "http://127.0.0.1:47653";

async function call(path, body) {
  try {
    const r = await fetch(BASE + path, body ? {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    } : {});
    return await r.json();
  } catch (e) {
    return { ok: false, error: "offline" };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, send) => {
  if (msg.type === "ping") call("/ping").then(send);
  else if (msg.type === "download") call("/download", { url: msg.url, mode: msg.mode }).then(send);
  else return false;
  return true;
});
