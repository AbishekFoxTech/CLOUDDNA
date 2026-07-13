(function () {
  const STORAGE_KEY = 'clouddna-theme';
  const root = document.documentElement;

  function applyTheme(theme) {
    root.setAttribute('data-bs-theme', theme);
    document.querySelectorAll('.theme-toggle-icon').forEach((icon) => {
      icon.className = 'theme-toggle-icon bi ' + (theme === 'dark' ? 'bi-sun-fill' : 'bi-moon-stars-fill');
    });
  }

  function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(saved || (prefersDark ? 'dark' : 'light'));
  }

  function toggleTheme() {
    const current = root.getAttribute('data-bs-theme') === 'dark' ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      btn.addEventListener('click', toggleTheme);
    });

    const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
    const sidebar = document.querySelector('.cdna-sidebar');
    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener('click', function () {
        sidebar.classList.toggle('show');
      });
    }

    setTimeout(function () {
      document.querySelectorAll('.alert-dismissible').forEach((alert) => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) closeBtn.click();
      });
    }, 5000);
  });
})();
