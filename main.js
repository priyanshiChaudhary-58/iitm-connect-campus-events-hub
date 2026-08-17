// ==========================================================
//  CEMS - Main JavaScript
// ==========================================================

// -- NAV TOGGLE --
function toggleNav() {
  const links = document.querySelector('.nav-links');
  if (links) links.classList.toggle('open');
}

// -- AUTO DISMISS FLASH MESSAGES --
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s, transform 0.5s';
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      setTimeout(() => el.remove(), 500);
    }, 4500);
  });
});

// =========================================
//  CHATBOT
// =========================================

let chatOpen = false;

function toggleChat() {
  const win = document.getElementById('chatWindow');
  const badge = document.getElementById('fabBadge');
  const icon = document.getElementById('fabIcon');

  if (!win || !badge || !icon) return;

  chatOpen = !chatOpen;
  win.classList.toggle('open', chatOpen);

  if (chatOpen) {
    badge.style.display = 'none';
    icon.textContent = '✕';

    const input = document.getElementById('chatInput');
    if (input) input.focus();

    scrollChat();
  } else {
    icon.textContent = '💬';
  }
}

function scrollChat() {
  const msgs = document.getElementById('chatMessages');
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
}

function addBubble(text, type) {
  const msgs = document.getElementById('chatMessages');
  if (!msgs) return null;

  const div = document.createElement('div');
  div.className = `chat-bubble ${type}-bubble`;
  div.textContent = text;
  msgs.appendChild(div);
  scrollChat();
  return div;
}

function showTyping() {
  const msgs = document.getElementById('chatMessages');
  if (!msgs) return;

  const div = document.createElement('div');
  div.className = 'chat-bubble bot-bubble typing-bubble';
  div.id = 'typingIndicator';
  div.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
  msgs.appendChild(div);
  scrollChat();
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  if (!input) return;

  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  addBubble(msg, 'user');
  showTyping();

  try {
    const res = await fetch('/api/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    removeTyping();
    addBubble(data.reply, 'bot');
  } catch (err) {
    removeTyping();
    addBubble('Sorry, something went wrong. Please try again! 😔', 'bot');
  }
}

function sendQuick(msg) {
  const input = document.getElementById('chatInput');
  if (!input) return;

  input.value = msg;
  sendChat();
}

// Close chat if click outside
document.addEventListener('click', function(e) {
  const win = document.getElementById('chatWindow');
  const fab = document.querySelector('.chatbot-fab');

  if (chatOpen && win && fab && !win.contains(e.target) && !fab.contains(e.target)) {
    toggleChat();
  }
});

// -- ANIMATE STATS ON SCROLL --
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.animationPlayState = 'running';
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('.event-card, .post-card, .admin-stat-card').forEach(el => {
  observer.observe(el);
});

// -- DATE INPUT: set min to today --
document.addEventListener('DOMContentLoaded', () => {
  const dateInputs = document.querySelectorAll('input[type="date"]');
  const today = new Date().toISOString().split('T')[0];
  dateInputs.forEach(d => {
    if (!d.min) d.min = today;
  });
});
// ── COUNTDOWN TIMERS ──
function updateCountdowns() {
  document.querySelectorAll('.countdown-timer').forEach(el => {
    const dateStr = el.getAttribute('data-date');
    if (!dateStr) return;

    const eventDate = new Date(dateStr + 'T00:00:00');
    const now       = new Date();
    const diff      = eventDate - now;

    if (diff <= 0) {
      el.textContent = '✅ Event Started';
      el.style.color = '#10b981';
      return;
    }

    const days  = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const mins  = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      el.textContent = `⏳ Starts in ${days}d ${hours}h`;
    } else if (hours > 0) {
      el.textContent = `⏳ Starts in ${hours}h ${mins}m`;
    } else {
      el.textContent = `⏳ Starts in ${mins}m`;
    }
  });
}

// Run immediately and refresh every minute
updateCountdowns();
setInterval(updateCountdowns, 60000);
