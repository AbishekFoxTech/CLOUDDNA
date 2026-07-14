(function () {
  const CATEGORY_COLORS = [
    '#4f46e5', '#2563eb', '#0891b2', '#059669', '#d97706',
    '#dc2626', '#7c3aed', '#db2777', '#65a30d', '#0d9488',
  ];
  const EDGE_COLORS = {
    similar: '#4f46e5',
    referenced: '#a855f7',
    same_category: '#9ca3af',
    same_keywords: '#14b8a6',
    duplicate: '#ef4444',
    manual: '#22c55e',
  };

  function categoryColor(category) {
    if (!category) return '#6b7280';
    let hash = 0;
    for (let i = 0; i < category.length; i++) {
      hash = category.charCodeAt(i) + ((hash << 5) - hash);
    }
    return CATEGORY_COLORS[Math.abs(hash) % CATEGORY_COLORS.length];
  }

  function buildStylesheet() {
    return [
      {
        selector: 'node',
        style: {
          'background-color': (ele) => categoryColor(ele.data('category')),
          'label': 'data(label)',
          'font-size': '10px',
          'color': '#e5e7eb',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 6,
          'width': 34,
          'height': 34,
          'border-width': (ele) => (ele.data('favorite') ? 3 : 0),
          'border-color': '#f59e0b',
          'text-wrap': 'ellipsis',
          'text-max-width': '90px',
        },
      },
      {
        selector: 'edge',
        style: {
          'width': (ele) => 1.5 + Math.min(ele.data('score') || 0, 1) * 3,
          'line-color': (ele) => EDGE_COLORS[ele.data('type')] || '#9ca3af',
          'target-arrow-color': (ele) => EDGE_COLORS[ele.data('type')] || '#9ca3af',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'opacity': 0.85,
        },
      },
      {
        selector: '.faded',
        style: { 'opacity': 0.12 },
      },
      {
        selector: '.highlighted',
        style: { 'opacity': 1, 'z-index': 999 },
      },
      {
        selector: 'node.highlighted',
        style: { 'border-width': 3, 'border-color': '#22d3ee' },
      },
    ];
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
  }

  function initGraph() {
    const loadingEl = document.getElementById('graph-loading');
    const emptyEl = document.getElementById('graph-empty');
    const cyContainer = document.getElementById('cy');

    fetch(window.CDNA_GRAPH_DATA_URL)
      .then((response) => response.json())
      .then((data) => {
        loadingEl.classList.add('d-none');

        if (!data.nodes || data.nodes.length < 2) {
          emptyEl.classList.remove('d-none');
          emptyEl.classList.add('d-flex');
          return;
        }

        cyContainer.style.display = 'block';

        const cy = cytoscape({
          container: cyContainer,
          elements: { nodes: data.nodes, edges: data.edges },
          style: buildStylesheet(),
          layout: { name: 'cose', animate: true, padding: 30 },
          wheelSensitivity: 0.25,
        });

        window.cdnaGraph = cy;

        const panelEmpty = document.getElementById('graph-panel-empty');
        const panelDoc = document.getElementById('graph-panel-doc');
        const panelTitle = document.getElementById('panel-doc-title');
        const panelCategory = document.getElementById('panel-doc-category');
        const panelStatus = document.getElementById('panel-doc-status');
        const panelLink = document.getElementById('panel-doc-link');
        const panelConnections = document.getElementById('panel-doc-connections');

        function selectNode(node) {
          const neighborhood = node.closedNeighborhood();
          cy.elements().removeClass('highlighted').addClass('faded');
          neighborhood.removeClass('faded').addClass('highlighted');

          panelEmpty.classList.add('d-none');
          panelDoc.classList.remove('d-none');
          panelTitle.textContent = node.data('label');
          panelCategory.textContent = node.data('category') || 'Uncategorized';
          panelStatus.textContent = node.data('ai_status');
          panelLink.href = node.data('url');

          const connectedEdges = node.connectedEdges();
          if (connectedEdges.length === 0) {
            panelConnections.innerHTML = '<li class="text-body-secondary">No connections yet.</li>';
          } else {
            panelConnections.innerHTML = connectedEdges.map((edge) => {
              const otherNode = edge.source().id() === node.id() ? edge.target() : edge.source();
              return `<li class="d-flex justify-content-between py-1 border-bottom">
                <span class="text-truncate" style="max-width: 65%;">${escapeHtml(otherNode.data('label'))}</span>
                <span class="badge bg-secondary-subtle text-secondary-emphasis">${escapeHtml(edge.data('type_label'))}</span>
              </li>`;
            }).join('');
          }
        }

        function clearSelection() {
          cy.elements().removeClass('faded highlighted');
          panelEmpty.classList.remove('d-none');
          panelDoc.classList.add('d-none');
        }

        cy.on('tap', 'node', (evt) => selectNode(evt.target));
        cy.on('tap', (evt) => {
          if (evt.target === cy) clearSelection();
        });

        document.getElementById('graph-zoom-in').addEventListener('click', () => {
          cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cyContainer.clientWidth / 2, y: cyContainer.clientHeight / 2 } });
        });
        document.getElementById('graph-zoom-out').addEventListener('click', () => {
          cy.zoom({ level: cy.zoom() / 1.3, renderedPosition: { x: cyContainer.clientWidth / 2, y: cyContainer.clientHeight / 2 } });
        });
        document.getElementById('graph-reset').addEventListener('click', () => {
          clearSelection();
          cy.fit(undefined, 30);
        });

        if (window.CDNA_GRAPH_FOCUS_PK) {
          const focusNode = cy.getElementById(String(window.CDNA_GRAPH_FOCUS_PK));
          if (focusNode && focusNode.length) {
            selectNode(focusNode);
            cy.animate({ center: { eles: focusNode }, zoom: 1.5 }, { duration: 400 });
          }
        }
      })
      .catch(() => {
        loadingEl.classList.add('d-none');
        emptyEl.classList.remove('d-none');
        emptyEl.classList.add('d-flex');
      });
  }

  document.addEventListener('DOMContentLoaded', initGraph);
})();
