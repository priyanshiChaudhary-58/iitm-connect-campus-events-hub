// countdown.js — Attaches live countdown timers to event cards
// Called automatically on DOMContentLoaded

function updateCountdowns() {
  const now = new Date();

  document.querySelectorAll('.card-countdown[data-date]').forEach(function(el) {
    const eventDate = el.getAttribute('data-date');
    if (!eventDate) return;

    const target = new Date(eventDate + 'T00:00:00');
    const diff   = target - now;

    const cdEl = el.querySelector('.countdown-value');
    if (!cdEl) return;

    if (diff <= 0) {
      cdEl.textContent = 'Event has passed';
      cdEl.style.color = 'var(--text-3)';
      return;
    }

    const days    = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours   = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      cdEl.textContent = `Starts in ${days}d ${hours}h`;
    } else if (hours > 0) {
      cdEl.textContent = `Starts in ${hours}h ${minutes}m`;
    } else {
      cdEl.textContent = `Starts in ${minutes}m — Today!`;
      cdEl.style.color = '#ef4444';
    }
  });
}

// Run immediately and then every 60 seconds
document.addEventListener('DOMContentLoaded', function() {
  updateCountdowns();
  setInterval(updateCountdowns, 60000);
});
