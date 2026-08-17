// carousel.js — Event spotlight carousel
// Auto-scrolls through events with dots + prev/next controls

(function() {
  let current    = 0;
  let total      = 0;
  let autoTimer  = null;
  const AUTO_MS  = 4000; // auto-advance every 4 seconds

  function getSlides() {
    return document.querySelectorAll('.carousel-slide');
  }
  function getDots() {
    return document.querySelectorAll('.carousel-dot');
  }

  function goTo(index) {
    const slides = getSlides();
    const dots   = getDots();
    total = slides.length;
    if (total === 0) return;

    // Clamp
    current = ((index % total) + total) % total;

    // Move track
    const track = document.getElementById('carouselTrack');
    if (track) track.style.transform = `translateX(-${current * 100}%)`;

    // Update dots
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
  }

  function startAuto() {
    stopAuto();
    autoTimer = setInterval(function() {
      goTo(current + 1);
    }, AUTO_MS);
  }

  function stopAuto() {
    if (autoTimer) clearInterval(autoTimer);
  }

  // Expose to HTML onclick handlers
  window.carouselNext    = function() { stopAuto(); goTo(current + 1); startAuto(); };
  window.carouselPrev    = function() { stopAuto(); goTo(current - 1); startAuto(); };
  window.carouselGoTo    = function(i){ stopAuto(); goTo(i); startAuto(); };

  document.addEventListener('DOMContentLoaded', function() {
    const slides = getSlides();
    total = slides.length;
    if (total === 0) return;

    goTo(0);
    startAuto();

    // Touch / swipe support
    let touchStartX = 0;
    const wrapper = document.querySelector('.carousel-wrapper');
    if (wrapper) {
      wrapper.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].clientX;
      }, { passive: true });
      wrapper.addEventListener('touchend', function(e) {
        const diff = touchStartX - e.changedTouches[0].clientX;
        if (Math.abs(diff) > 50) {
          if (diff > 0) window.carouselNext();
          else          window.carouselPrev();
        }
      }, { passive: true });
    }

    // Pause on hover
    const section = document.querySelector('.carousel-section');
    if (section) {
      section.addEventListener('mouseenter', stopAuto);
      section.addEventListener('mouseleave', startAuto);
    }
  });
})();
