(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return match[1];
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    const markAllBtn = document.getElementById('mark-all-notifications-read');
    if (!markAllBtn) return;

    markAllBtn.addEventListener('click', function (event) {
      event.preventDefault();
      fetch(window.CDNA_MARK_ALL_NOTIFICATIONS_READ_URL, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCsrfToken(),
        },
      })
        .then((response) => response.json())
        .then(() => {
          document.querySelectorAll('.dropdown-item.fw-semibold').forEach((item) => {
            item.classList.remove('fw-semibold');
          });
          const badge = document.querySelector('.theme-toggle-btn .badge');
          if (badge) badge.remove();
        })
        .catch(() => {});
    });
  });
})();
