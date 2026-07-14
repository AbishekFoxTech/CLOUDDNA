(function () {
  const PALETTE = [
    '#4f46e5', '#2563eb', '#0891b2', '#059669', '#d97706',
    '#dc2626', '#7c3aed', '#db2777', '#65a30d', '#0d9488',
  ];

  function readJson(id) {
    const el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : { labels: [], data: [] };
  }

  function initCharts() {
    const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    const textColor = isDark ? '#e5e7eb' : '#374151';
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';

    const categoryData = readJson('category-chart-data');
    const monthData = readJson('month-chart-data');
    const aiStatusData = readJson('ai-status-chart-data');
    const keywordData = readJson('keyword-chart-data');

    const categoryEl = document.getElementById('categoryPieChart');
    if (categoryEl) {
      new Chart(categoryEl, {
        type: 'pie',
        data: {
          labels: categoryData.labels,
          datasets: [{ data: categoryData.data, backgroundColor: PALETTE }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
      });
    }

    const aiStatusEl = document.getElementById('aiStatusDoughnutChart');
    if (aiStatusEl) {
      new Chart(aiStatusEl, {
        type: 'doughnut',
        data: {
          labels: aiStatusData.labels,
          datasets: [{ data: aiStatusData.data, backgroundColor: PALETTE }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
      });
    }

    const monthEl = document.getElementById('monthLineChart');
    if (monthEl) {
      new Chart(monthEl, {
        type: 'line',
        data: {
          labels: monthData.labels,
          datasets: [{
            label: 'Uploads',
            data: monthData.data,
            borderColor: '#4f46e5',
            backgroundColor: 'rgba(79, 70, 229, 0.15)',
            fill: true,
            tension: 0.3,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }

    const keywordEl = document.getElementById('keywordBarChart');
    if (keywordEl) {
      new Chart(keywordEl, {
        type: 'bar',
        data: {
          labels: keywordData.labels,
          datasets: [{ label: 'Occurrences', data: keywordData.data, backgroundColor: '#2563eb' }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }
  }

  document.addEventListener('DOMContentLoaded', initCharts);
})();
