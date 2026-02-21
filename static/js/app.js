function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

async function saveGpsToServer(latitude, longitude) {
  const csrftoken = getCookie('csrftoken');
  try {
    await fetch('/agents/update-gps/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken || '',
      },
      body: JSON.stringify({ latitude, longitude }),
    });
  } catch (e) {
    // ignore
  }
}

function setGpsStatus(text) {
  const el = document.getElementById('gpsStatus');
  if (!el) return;
  el.textContent = text;
}

function setupFloatRequestGps() {
  const requestType = document.querySelector('select[name="request_type"]');
  const latInput = document.querySelector('input[name="requester_latitude"]');
  const lngInput = document.querySelector('input[name="requester_longitude"]');
  if (!requestType || !latInput || !lngInput) return;

  async function ensureGpsIfNeeded() {
    const type = requestType.value;
    if (type === 'E_CASH') {
      setGpsStatus('');
      latInput.value = '';
      lngInput.value = '';
      return;
    }

    if (type !== 'PHYSICAL_CASH') {
      setGpsStatus('');
      latInput.value = '';
      lngInput.value = '';
      return;
    }

    if (!navigator.geolocation) {
      setGpsStatus('GPS not supported in this browser.');
      return;
    }

    setGpsStatus('Getting your location...');

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const latitude = pos.coords.latitude;
        const longitude = pos.coords.longitude;
        latInput.value = String(latitude);
        lngInput.value = String(longitude);
        setGpsStatus('Location captured.');
        await saveGpsToServer(latitude, longitude);
      },
      (err) => {
        setGpsStatus('Location permission denied. Physical cash needs GPS.');
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  requestType.addEventListener('change', ensureGpsIfNeeded);
  ensureGpsIfNeeded();
}

document.addEventListener('DOMContentLoaded', () => {
  setupFloatRequestGps();
  setupChargePreview();
  setupIncomingPopup();
  setupIncomingAutoRefresh();
  setupRequestChat();
});

function setupChargePreview() {
  const form = document.getElementById('floatRequestForm');
  if (!form) return;

  const amountInput = form.querySelector('input[name="amount"]');
  const preview = document.getElementById('chargePreview');
  if (!amountInput || !preview) return;

  const RATE = 0.005; // 0.50 per 100 GHS

  function toMoney(n) {
    if (!Number.isFinite(n)) return '0.00';
    return n.toFixed(2);
  }

  function render() {
    const raw = String(amountInput.value || '').trim();
    const amount = Number(raw);
    if (!raw || !Number.isFinite(amount) || amount <= 0) {
      preview.style.display = 'none';
      preview.textContent = '';
      return;
    }

    const fee = amount * RATE;
    const total = amount + fee;
    preview.style.display = '';
    preview.textContent = `Service charge (GHS 0.50 per 100): GHS ${toMoney(fee)}. Total cost: GHS ${toMoney(total)}.`;
  }

  amountInput.addEventListener('input', render);
  amountInput.addEventListener('change', render);
  render();
}

function setupIncomingPopup() {
  const modalEl = document.getElementById('incomingRequestModal');
  const bs = window.bootstrap;
  if (!modalEl || !bs || !bs.Modal) return;

  const requesterEl = document.getElementById('incomingReqRequester');
  const amountEl = document.getElementById('incomingReqAmount');
  const openBtn = document.getElementById('incomingReqOpenBtn');

  const modal = bs.Modal.getOrCreateInstance ? bs.Modal.getOrCreateInstance(modalEl) : new bs.Modal(modalEl);

  const shownNotifIds = new Set();

  function playAlert() {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.value = 0.05;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      setTimeout(() => {
        osc.stop();
        ctx.close();
      }, 250);
    } catch (e) {
      // ignore
    }

    try {
      if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
    } catch (e2) {
      // ignore
    }
  }

  async function ackNotification(notifId) {
    const csrftoken = getCookie('csrftoken');
    try {
      await fetch(`/requests/notifications/${encodeURIComponent(String(notifId))}/ack/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrftoken || '',
        },
      });
    } catch (e) {
      // ignore
    }
  }

  async function poll() {
    try {
      const res = await fetch('/requests/notifications/poll/');
      const data = await res.json();
      if (!data.ok) return;

      const notifs = data.notifications || [];
      for (const n of notifs) {
        if (shownNotifIds.has(n.id)) continue;
        shownNotifIds.add(n.id);
        const reqId = String(n.request_id);

        if (requesterEl) requesterEl.textContent = n.requester;
        if (amountEl) amountEl.textContent = `GHS ${n.amount}`;
        if (openBtn) {
          openBtn.href = `/requests/${encodeURIComponent(reqId)}/`;
          openBtn.onclick = () => {
            ackNotification(n.id);
            return true;
          };
        }
        playAlert();
        setTimeout(() => modal.show(), 50);
      }
    } catch (e) {
      // ignore
    }
  }

  poll();
  setInterval(poll, 5000);
}

function setupIncomingAutoRefresh() {
  const tbody = document.getElementById('incomingTbody');
  if (!tbody) return;

  let latestId = Number(tbody.getAttribute('data-latest-id') || '0');
  if (!Number.isFinite(latestId)) latestId = 0;

  function makeRow(r) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>#${escapeHtml(r.id)}</td>
      <td>${escapeHtml(r.requester)}</td>
      <td>GHS ${escapeHtml(r.amount)}</td>
      <td><span class="badge bg-light text-dark border">${escapeHtml(r.status_display)}</span></td>
      <td><a class="btn btn-sm btn-fl-outline" href="/requests/${encodeURIComponent(String(r.id))}/">Open</a></td>
    `;
    return tr;
  }

  async function poll() {
    try {
      const res = await fetch(`/requests/incoming/feed/?since_id=${encodeURIComponent(String(latestId))}`);
      const data = await res.json();
      if (!data.ok) return;

      const newReqs = data.requests || [];
      if (!newReqs.length) return;

      const emptyRow = document.getElementById('incomingEmptyRow');
      if (emptyRow) emptyRow.remove();

      for (const r of newReqs) {
        const idNum = Number(r.id);
        if (Number.isFinite(idNum)) latestId = Math.max(latestId, idNum);
        tbody.prepend(makeRow(r));
      }

      tbody.setAttribute('data-latest-id', String(latestId));
    } catch (e) {
      // ignore
    }
  }

  poll();
  setInterval(poll, 3000);
}

function setupRequestChat() {
  const chatBox = document.getElementById('chatBox');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatMessage');
  const chatAttachment = document.getElementById('chatAttachment');
  const chatFileName = document.getElementById('chatFileName');
  if (!chatBox) return;

  const requestId = chatBox.getAttribute('data-request-id');
  if (!requestId) return;

  const currentUserId = Number(chatBox.getAttribute('data-current-user-id') || '0');

  let sinceId = 0;

  function appendMessage(m) {
    const row = document.createElement('div');
    const isMe = Number(m.sender_user_id) === currentUserId;
    row.className = `fl-chat-row ${isMe ? 'me' : 'them'}`;

    const bubble = document.createElement('div');
    bubble.className = 'fl-chat-bubble';

    const text = document.createElement('div');
    text.innerHTML = escapeHtml(m.message || '');
    bubble.appendChild(text);

    if (m.attachment_url) {
      const img = document.createElement('img');
      img.className = 'fl-chat-attachment';
      img.src = m.attachment_url;
      img.alt = 'attachment';
      bubble.appendChild(img);
    }

    const meta = document.createElement('div');
    meta.className = 'fl-chat-meta';
    const dt = m.created_at ? new Date(m.created_at) : null;
    const when = dt && !Number.isNaN(dt.getTime()) ? dt.toLocaleString() : '';
    meta.textContent = isMe ? when : `${m.sender} · ${when}`;
    bubble.appendChild(meta);

    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  async function poll() {
    try {
      const res = await fetch(`/requests/${encodeURIComponent(requestId)}/messages/?since_id=${encodeURIComponent(String(sinceId))}`);
      if (!res.ok) {
        console.warn('Chat poll failed', res.status);
        return;
      }
      const data = await res.json();
      if (!data.ok) {
        console.warn('Chat poll not ok', data);
        return;
      }
      const msgs = data.messages || [];
      for (const m of msgs) {
        appendMessage(m);
        sinceId = Math.max(sinceId, Number(m.id) || sinceId);
      }
    } catch (e) {
      console.warn('Chat poll exception', e);
    }
  }

  if (chatForm && chatInput) {
    if (chatAttachment && chatFileName) {
      const updateFileName = () => {
        const file = (chatAttachment.files && chatAttachment.files[0]) ? chatAttachment.files[0] : null;
        chatFileName.textContent = file ? file.name : '';
      };
      chatAttachment.addEventListener('change', updateFileName);
      updateFileName();
    }

    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      const file = chatAttachment ? (chatAttachment.files && chatAttachment.files[0]) : null;
      if (!text && !file) return;

      const csrftoken = getCookie('csrftoken');
      const body = new FormData();
      body.set('message', text);
      if (file) body.set('attachment', file);
      try {
        const res = await fetch(`/requests/${encodeURIComponent(requestId)}/messages/send/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrftoken || '',
          },
          body,
        });
        let data = null;
        try {
          data = await res.json();
        } catch (jsonErr) {
          console.warn('Chat send JSON parse failed', jsonErr);
        }

        if (!res.ok || !data || !data.ok) {
          const msg = (data && data.error) ? data.error : `Send failed (HTTP ${res.status})`;
          console.warn('Chat send failed', res.status, data);
          alert(msg);
          return;
        }

        if (data.ok) {
          chatInput.value = '';
          if (chatAttachment) chatAttachment.value = '';
          if (chatFileName) chatFileName.textContent = '';
          poll();
        }
      } catch (e2) {
        console.warn('Chat send exception', e2);
        alert('Send failed. Check your connection and try again.');
      }
    });
  }

  poll();
  setInterval(poll, 3000);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
