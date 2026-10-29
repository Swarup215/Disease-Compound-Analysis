// Biomedical AI — Frontend Application Logic

let currentResults = null;

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const form = document.getElementById('pipelineForm');
  const diseaseInput = document.getElementById('diseaseInput');
  const clearDiseaseBtn = document.getElementById('clearDiseaseBtn');
  const targetLimitSlider = document.getElementById('targetLimitSlider');
  const targetLimitVal = document.getElementById('targetLimitVal');
  const papersLimitSlider = document.getElementById('papersLimitSlider');
  const papersLimitVal = document.getElementById('papersLimitVal');
  const structWeightSlider = document.getElementById('structWeightSlider');
  const structWeightVal = document.getElementById('structWeightVal');
  const litWeightSlider = document.getElementById('litWeightSlider');
  const litWeightVal = document.getElementById('litWeightVal');
  const minScoreSlider = document.getElementById('minScoreSlider');
  const minScoreVal = document.getElementById('minScoreVal');
  const quickTags = document.querySelectorAll('.disease-tag');

  const progressSection = document.getElementById('progressSection');
  const resultsSection = document.getElementById('resultsSection');
  const runPipelineBtn = document.getElementById('runPipelineBtn');
  const progressPercent = document.getElementById('progressPercent');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressStageText = document.getElementById('progressStageText');

  // Sync Slider Display Values
  targetLimitSlider.addEventListener('input', (e) => targetLimitVal.textContent = e.target.value);
  papersLimitSlider.addEventListener('input', (e) => papersLimitVal.textContent = e.target.value);
  minScoreSlider.addEventListener('input', (e) => minScoreVal.textContent = parseFloat(e.target.value).toFixed(2));
  
  structWeightSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    structWeightVal.textContent = val.toFixed(2);
    const litVal = Math.max(0, 1.0 - val);
    litWeightSlider.value = litVal;
    litWeightVal.textContent = litVal.toFixed(2);
  });

  litWeightSlider.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    litWeightVal.textContent = val.toFixed(2);
    const structVal = Math.max(0, 1.0 - val);
    structWeightSlider.value = structVal;
    structWeightVal.textContent = structVal.toFixed(2);
  });

  // Autocomplete & Spelling Suggestion Dropdown
  const diseaseSuggestions = document.getElementById('diseaseSuggestions');
  const diseaseErrorAlert = document.getElementById('diseaseErrorAlert');
  let suggestTimeout = null;
  let activeIndex = -1;

  function hideSuggestions() {
    if (diseaseSuggestions) {
      diseaseSuggestions.classList.add('hidden');
      diseaseSuggestions.innerHTML = '';
    }
    activeIndex = -1;
  }

  function hideErrorAlert() {
    if (diseaseErrorAlert) {
      diseaseErrorAlert.classList.add('hidden');
      diseaseErrorAlert.innerHTML = '';
    }
  }

  async function fetchSuggestions(query) {
    if (!query || query.length < 2) {
      hideSuggestions();
      return;
    }
    try {
      const resp = await fetch(`/api/suggest?q=${encodeURIComponent(query)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      renderSuggestions(data.suggestions || []);
    } catch (e) {
      console.warn("Suggestion fetch error:", e);
    }
  }

  function renderSuggestions(suggestions) {
    if (!diseaseSuggestions || !suggestions || suggestions.length === 0) {
      hideSuggestions();
      return;
    }

    diseaseSuggestions.innerHTML = '';
    activeIndex = -1;

    suggestions.forEach((item, idx) => {
      const div = document.createElement('div');
      div.className = 'suggestion-item';
      div.setAttribute('data-idx', idx);

      const isSpelling = item.source === 'Spelling Correction';
      const badgeClass = isSpelling ? 'suggestion-badge spelling' : 'suggestion-badge';

      div.innerHTML = `
        <div class="suggestion-main">
          <span class="suggestion-name">${escapeHtml(item.name)}</span>
          <span class="suggestion-id">${escapeHtml(item.id)}</span>
        </div>
        <span class="${badgeClass}">${escapeHtml(item.source)}</span>
      `;

      div.addEventListener('mousedown', (e) => {
        e.preventDefault();
        selectSuggestion(item.name);
      });

      diseaseSuggestions.appendChild(div);
    });

    diseaseSuggestions.classList.remove('hidden');
  }

  function selectSuggestion(name) {
    diseaseInput.value = name;
    hideSuggestions();
    hideErrorAlert();
    diseaseInput.focus();
  }

  diseaseInput.addEventListener('input', (e) => {
    hideErrorAlert();
    clearTimeout(suggestTimeout);
    const val = e.target.value.trim();
    suggestTimeout = setTimeout(() => fetchSuggestions(val), 150);
  });

  diseaseInput.addEventListener('keydown', (e) => {
    if (!diseaseSuggestions) return;
    const items = diseaseSuggestions.querySelectorAll('.suggestion-item');
    if (diseaseSuggestions.classList.contains('hidden') || items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveSuggestion(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveSuggestion(items);
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < items.length) {
        e.preventDefault();
        const name = items[activeIndex].querySelector('.suggestion-name').textContent;
        selectSuggestion(name);
      }
    } else if (e.key === 'Escape') {
      hideSuggestions();
    }
  });

  function updateActiveSuggestion(items) {
    items.forEach((item, i) => {
      if (i === activeIndex) {
        item.classList.add('active');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('active');
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (diseaseInput && diseaseSuggestions && !diseaseInput.contains(e.target) && !diseaseSuggestions.contains(e.target)) {
      hideSuggestions();
    }
  });

  // Quick disease tags
  quickTags.forEach(tag => {
    tag.addEventListener('click', () => {
      diseaseInput.value = tag.getAttribute('data-disease');
      hideSuggestions();
      hideErrorAlert();
      diseaseInput.focus();
    });
  });

  clearDiseaseBtn.addEventListener('click', () => {
    diseaseInput.value = '';
    hideSuggestions();
    hideErrorAlert();
    diseaseInput.focus();
  });

  // Tab switching
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      document.getElementById(tabId)?.classList.add('active');
    });
  });

  // Form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideSuggestions();
    hideErrorAlert();
    const disease = diseaseInput.value.trim();
    if (!disease) return;

    const payload = {
      disease: disease,
      target_limit: parseInt(targetLimitSlider.value),
      papers_per_target: parseInt(papersLimitSlider.value),
      min_score: parseFloat(minScoreSlider.value),
      structured_weight: parseFloat(structWeightSlider.value),
      literature_weight: parseFloat(litWeightSlider.value)
    };

    startPipelineExecution(payload);
  });

  // Filtering targets
  const targetFilterInput = document.getElementById('targetFilterInput');
  targetFilterInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    document.querySelectorAll('.target-card').forEach(card => {
      const text = card.textContent.toLowerCase();
      card.style.display = text.includes(query) ? 'block' : 'none';
    });
  });

  // Expand / Collapse all
  document.getElementById('expandAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.evidence-drawer').forEach(d => d.classList.add('open'));
    document.querySelectorAll('.target-expand-col button').forEach(b => b.classList.add('expanded'));
  });

  document.getElementById('collapseAllBtn').addEventListener('click', () => {
    document.querySelectorAll('.evidence-drawer').forEach(d => d.classList.remove('open'));
    document.querySelectorAll('.target-expand-col button').forEach(b => b.classList.remove('expanded'));
  });

  // Export handlers
  document.getElementById('downloadJsonBtn').addEventListener('click', () => {
    if (!currentResults) return;
    downloadFile(JSON.stringify(currentResults, null, 2), `${slugify(currentResults.disease.canonical_name)}_targets.json`, 'application/json');
  });

  document.getElementById('downloadCsvBtn').addEventListener('click', () => {
    if (!currentResults || !currentResults.targets) return;
    const csv = convertTargetsToCSV(currentResults.targets);
    downloadFile(csv, `${slugify(currentResults.disease.canonical_name)}_targets.csv`, 'text/csv');
  });
});

async function startPipelineExecution(payload) {
  const progressSection = document.getElementById('progressSection');
  const resultsSection = document.getElementById('resultsSection');
  const runPipelineBtn = document.getElementById('runPipelineBtn');
  const progressPercent = document.getElementById('progressPercent');
  const progressBarFill = document.getElementById('progressBarFill');
  const progressStageText = document.getElementById('progressStageText');

  // UI state
  progressSection.classList.remove('hidden');
  resultsSection.classList.add('hidden');
  runPipelineBtn.disabled = true;
  runPipelineBtn.style.opacity = '0.6';

  let pct = 5;
  const stepItems = [
    document.getElementById('step1'),
    document.getElementById('step2'),
    document.getElementById('step3'),
    document.getElementById('step4'),
    document.getElementById('step5'),
    document.getElementById('step6'),
    document.getElementById('step7')
  ];

  function setStep(idx, text) {
    progressStageText.textContent = text;
    stepItems.forEach((st, i) => {
      if (i < idx) {
        st.className = 'step-item completed';
      } else if (i === idx) {
        st.className = 'step-item active';
      } else {
        st.className = 'step-item';
      }
    });
  }

  setStep(0, "Normalizing disease name and resolving ontologies...");

  const progressInterval = setInterval(() => {
    if (pct < 92) {
      pct += Math.floor(Math.random() * 6) + 2;
      if (pct > 92) pct = 92;
      progressPercent.textContent = `${pct}%`;
      progressBarFill.style.width = `${pct}%`;

      if (pct >= 15 && pct < 35) setStep(1, "Retrieving disease-target associations from Open Targets...");
      else if (pct >= 35 && pct < 55) setStep(2, `Harvesting literature across PubMed, Europe PMC & Open Targets...`);
      else if (pct >= 55 && pct < 70) setStep(3, "Embedding passages & indexing FAISS vector store...");
      else if (pct >= 70 && pct < 82) setStep(4, "Extracting biological evidence assertions from text...");
      else if (pct >= 82 && pct < 90) setStep(5, "Fusing structured database & literature evidence...");
      else if (pct >= 90) setStep(6, "Prioritizing candidate targets & building report...");
    }
  }, 400);

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    clearInterval(progressInterval);

    if (!response.ok) {
      const errData = await response.json();
      const errorObj = new Error(errData.message || 'Pipeline analysis failed');
      errorObj.data = errData;
      throw errorObj;
    }

    const data = await response.json();
    currentResults = data;

    pct = 100;
    progressPercent.textContent = '100%';
    progressBarFill.style.width = '100%';
    stepItems.forEach(s => s.className = 'step-item completed');
    progressStageText.textContent = 'Analysis Completed Successfully!';

    setTimeout(() => {
      progressSection.classList.add('hidden');
      renderResults(data);
      resultsSection.classList.remove('hidden');
      runPipelineBtn.disabled = false;
      runPipelineBtn.style.opacity = '1';
      const fetchBtn = document.getElementById('fetchCompoundsBtn');
      if (fetchBtn) fetchBtn.disabled = false;
      resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 450);

  } catch (err) {
    clearInterval(progressInterval);
    progressSection.classList.add('hidden');
    runPipelineBtn.disabled = false;
    runPipelineBtn.style.opacity = '1';

    if (err.data && (err.data.suggestions || err.data.status === 'unresolved_disease')) {
      renderErrorAlert(err.data.query || payload.disease, err.data.message, err.data.suggestions);
    } else {
      alert(`Pipeline error: ${err.message}`);
    }
  }
}

function renderErrorAlert(query, message, suggestions) {
  const alertEl = document.getElementById('diseaseErrorAlert');
  if (!alertEl) return;

  const pillsHtml = (suggestions || []).map(s => `
    <button type="button" class="suggestion-pill-btn" data-name="${escapeHtml(s.name)}">
      ✨ ${escapeHtml(s.name)} (${escapeHtml(s.id)})
    </button>
  `).join('');

  alertEl.innerHTML = `
    <div class="alert-warning-title">
      <span>⚠️ Unrecognized or Misspelled Disease Condition</span>
    </div>
    <div>
      We could not confidently identify <strong>"${escapeHtml(query)}"</strong>.
      Please type the disease name again or select a suggested correct spelling below:
    </div>
    <div class="suggestion-pills-row">
      ${pillsHtml.length ? pillsHtml : '<span style="font-size: 0.8rem; color: var(--text-dim);">No close spelling matches found. Try typing another term.</span>'}
    </div>
  `;

  alertEl.classList.remove('hidden');

  alertEl.querySelectorAll('.suggestion-pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.getAttribute('data-name');
      const diseaseInput = document.getElementById('diseaseInput');
      if (diseaseInput && name) {
        diseaseInput.value = name;
        alertEl.classList.add('hidden');
        document.getElementById('pipelineForm').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    });
  });

  alertEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function renderResults(data) {
  const disease = data.disease || {};
  const metrics = data.metrics || {};
  const targets = data.targets || [];
  const papers = data.papers || [];
  const graph = data.graph || {};

  document.getElementById('resDiseaseName').textContent = disease.canonical_name || disease.input;
  document.getElementById('resTotalProteins').textContent = metrics.total_targets_found || 0;
  document.getElementById('resAnalyzedProteins').textContent = `${metrics.analyzed_targets || 0} candidate targets`;
  document.getElementById('resTotalPapers').textContent = metrics.total_unique_papers || 0;
  document.getElementById('resTotalEvidence').textContent = metrics.total_evidence_extracted || 0;
  document.getElementById('resElapsed').textContent = `${data.elapsed_seconds || 0}s elapsed`;
  document.getElementById('tabPapersCount').textContent = papers.length;
  const srcEl = document.getElementById('resPaperSourceLabel');
  if (srcEl) {
    srcEl.textContent = (metrics.literature_sources && metrics.literature_sources.length)
      ? metrics.literature_sources.join(', ')
      : 'PubMed, Europe PMC & Open Targets';
  }

  const badgesContainer = document.getElementById('resDiseaseBadges');
  badgesContainer.innerHTML = '';
  const ids = disease.identifiers || {};
  if (ids.mondo) badgesContainer.appendChild(createBadge('MONDO: ' + ids.mondo, 'badge-mono'));
  if (ids.efo) badgesContainer.appendChild(createBadge('EFO: ' + ids.efo, 'badge-mono'));
  if (ids.doid) badgesContainer.appendChild(createBadge('DOID: ' + ids.doid, 'badge-mono'));
  if (ids.mesh) badgesContainer.appendChild(createBadge('MeSH: ' + ids.mesh, 'badge-mono'));

  const targetsList = document.getElementById('targetsList');
  targetsList.innerHTML = '';

  targets.forEach((target) => {
    const card = document.createElement('div');
    card.className = `target-card ${target.rank === 1 ? 'rank-1' : ''}`;

    let rankClass = 'rank-badge';
    if (target.rank === 1) rankClass += ' gold';
    else if (target.rank === 2) rankClass += ' silver';
    else if (target.rank === 3) rankClass += ' bronze';

    const evidenceCount = target.evidence_count || 0;
    const hasEvidence = evidenceCount > 0;

    let evidenceItemsHtml = '';
    if (hasEvidence && target.evidence_items) {
      evidenceItemsHtml = target.evidence_items.map((ev, idx) => {
        const strengthClass = ev.evidence_strength || 'weak';
        return `
          <div class="evidence-item-card ${strengthClass}">
            <div class="evidence-item-header">
              <span class="evidence-paper-title">
                ${ev.title || 'Scientific Publication Abstract'}
              </span>
              <div class="evidence-badges-row">
                ${ev.source ? `<span class="badge badge-indigo">${escapeHtml(ev.source)}</span>` : ''}
                ${ev.pmid ? `<a href="${ev.url || ev.pubmed_url || ('https://pubmed.ncbi.nlm.nih.gov/' + ev.pmid)}" target="_blank" rel="noopener" class="pubmed-link">${ev.pmid.startsWith('PMC') || ev.pmid.startsWith('PPR') ? ev.pmid : 'PMID: ' + ev.pmid} ↗</a>` : (ev.url ? `<a href="${ev.url}" target="_blank" rel="noopener" class="pubmed-link">Paper Link ↗</a>` : '')}
                <span class="badge badge-purple">${formatLabel(ev.evidence_type)}</span>
                <span class="badge ${ev.relation === 'no_association' ? 'badge-rose' : 'badge-cyan'}">${ev.relation}</span>
                <span class="badge ${ev.evidence_strength === 'strong' ? 'badge-emerald' : ev.evidence_strength === 'moderate' ? 'badge-cyan' : 'badge-amber'}">${ev.evidence_strength.toUpperCase()}</span>
                <span class="badge badge-mono">Conf: ${(ev.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
            
            <div class="evidence-quote-box">
              "${escapeHtml(ev.evidence_text)}"
            </div>

            <div class="evidence-citation-meta">
              ${ev.journal ? `<span>🏛️ <strong>Journal:</strong> ${escapeHtml(ev.journal)}</span>` : ''}
              ${ev.publication_date ? `<span>📅 <strong>Date:</strong> ${escapeHtml(ev.publication_date)}</span>` : ''}
              ${ev.authors && ev.authors.length ? `<span>✍️ <strong>Authors:</strong> ${escapeHtml(ev.authors.slice(0, 3).join(', '))}${ev.authors.length > 3 ? ' et al.' : ''}</span>` : ''}
              ${ev.doi ? `<span>🔗 <strong>DOI:</strong> ${escapeHtml(ev.doi)}</span>` : ''}
            </div>
          </div>
        `;
      }).join('');
    } else {
      evidenceItemsHtml = `
        <div style="padding: 12px; color: var(--text-dim); font-size: 0.88rem;">
          No explicit sentence-level co-occurrence assertion extracted in retrieved abstracts for this target.
        </div>
      `;
    }

    card.innerHTML = `
      <div class="target-main-row">
        <div class="target-rank-col">
          <div class="${rankClass}">#${target.rank}</div>
        </div>

        <div class="target-info-col">
          <h4>
            <span>${escapeHtml(target.target_symbol)}</span>
            <span class="badge badge-mono">${escapeHtml(target.target_id)}</span>
          </h4>
          <p class="target-full-name" title="${escapeHtml(target.target_name)}">${escapeHtml(target.target_name)}</p>
        </div>

        <div class="target-score-col">
          <span class="score-title">Fused Score</span>
          <span class="score-num">${(target.fused_score * 100).toFixed(1)}%</span>
          <div class="score-bar-mini">
            <div class="score-bar-fill" style="width: ${target.fused_score * 100}%;"></div>
          </div>
        </div>

        <div class="score-breakdown-col target-cell-hide-mobile">
          <div class="breakdown-row">
            <span>Open Targets:</span>
            <span>${(target.structured_score * 100).toFixed(1)}%</span>
          </div>
          <div class="breakdown-row">
            <span>Literature Score:</span>
            <span>${(target.literature_score * 100).toFixed(1)}%</span>
          </div>
        </div>

        <div class="evidence-badge-col target-cell-hide-mobile">
          <span class="evidence-pill ${hasEvidence ? 'found' : 'none'}">
            ${hasEvidence ? `✓ ${evidenceCount} Evidence Claims` : 'No direct claims'}
          </span>
          ${hasEvidence ? `
            <span style="font-size: 0.72rem; color: var(--text-dim);">
              ${target.strong_evidence_count} strong · ${target.moderate_evidence_count} mod
            </span>
          ` : ''}
        </div>

        <div class="target-expand-col">
          <button type="button" class="expand-toggle-btn" title="View where literature evidence is found">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        </div>
      </div>

      <div class="evidence-drawer" id="drawer-${target.target_symbol}">
        <div class="drawer-header">
          <h5>
            <span>📖 Literature Evidence Sources for ${escapeHtml(target.target_symbol)}</span>
            <span class="badge badge-cyan">${evidenceCount} assertions</span>
          </h5>
          <span style="font-size: 0.78rem; color: var(--text-muted);">
            Papers reviewed: ${(target.papers_referenced || []).length}
          </span>
        </div>

        <div class="evidence-items-grid">
          ${evidenceItemsHtml}
        </div>
      </div>
    `;

    const btn = card.querySelector('.expand-toggle-btn');
    const drawer = card.querySelector('.evidence-drawer');
    btn.addEventListener('click', () => {
      const isOpen = drawer.classList.contains('open');
      drawer.classList.toggle('open', !isOpen);
      btn.classList.toggle('expanded', !isOpen);
    });

    targetsList.appendChild(card);
  });

  const papersList = document.getElementById('papersList');
  papersList.innerHTML = '';
  papers.forEach(p => {
    const pCard = document.createElement('div');
    pCard.className = 'paper-card';
    pCard.innerHTML = `
      <div class="paper-card-top">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
          <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
            <a href="${p.url || p.pubmed_url || ('https://pubmed.ncbi.nlm.nih.gov/' + p.pmid)}" target="_blank" rel="noopener" class="pubmed-link">${p.pmid.startsWith('PMC') || p.pmid.startsWith('PPR') ? p.pmid : 'PMID: ' + p.pmid} ↗</a>
            ${p.source ? `<span class="badge badge-indigo">${escapeHtml(p.source)}</span>` : ''}
            ${p.pmcid ? `<a href="https://europepmc.org/article/PMC/${p.pmcid}" target="_blank" rel="noopener" class="badge badge-emerald">PMC: ${escapeHtml(p.pmcid)} ↗</a>` : ''}
          </div>
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            ${(p.target_symbols || []).map(s => `<span class="badge badge-mono">${s}</span>`).join('')}
          </div>
        </div>
        <h4 class="paper-card-title">${escapeHtml(p.title || 'Untitled Scientific Paper')}</h4>
        <p class="paper-card-authors">${escapeHtml((p.authors || []).slice(0, 4).join(', '))}${p.authors && p.authors.length > 4 ? ' et al.' : ''}</p>
      </div>
      <div class="paper-card-meta">
        <span>🏛️ ${escapeHtml(p.journal || 'Journal')}</span>
        <span>📅 ${escapeHtml(p.publication_date || 'N/A')}</span>
        ${p.doi ? `<span>🔗 DOI: ${escapeHtml(p.doi)}</span>` : ''}
      </div>
    `;
    papersList.appendChild(pCard);
  });

  document.getElementById('graphDiseaseCount').textContent = graph.diseases_count || 1;
  document.getElementById('graphTargetCount').textContent = graph.targets_count || targets.length;
  document.getElementById('graphPaperCount').textContent = graph.papers_count || papers.length;
  document.getElementById('graphEvidenceCount').textContent = graph.evidence_count || 0;
  document.getElementById('graphEdgeCount').textContent = graph.edges_count || (graph.edges || []).length;

  const edgesList = document.getElementById('edgesList');
  edgesList.innerHTML = '';
  (graph.edges || []).slice(0, 40).forEach(e => {
    const row = document.createElement('div');
    row.className = 'edge-row';
    row.innerHTML = `
      <span class="edge-src">${escapeHtml(e.source_id)}</span>
      <span class="edge-rel">--[${escapeHtml(e.relation)}]--></span>
      <span class="edge-tgt">${escapeHtml(e.target_id)}</span>
    `;
    edgesList.appendChild(row);
  });

  document.getElementById('jsonViewer').querySelector('code').textContent = JSON.stringify(data, null, 2);
}

function createBadge(text, className) {
  const s = document.createElement('span');
  s.className = `badge ${className}`;
  s.textContent = text;
  return s;
}

function formatLabel(str) {
  if (!str) return 'Unknown';
  return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function slugify(text) {
  return (text || 'biomedical').toString().toLowerCase().trim().replace(/\s+/g, '_').replace(/[^\w-]+/g, '');
}

function convertTargetsToCSV(targets) {
  const headers = ['Rank', 'Symbol', 'Target_ID', 'Name', 'Fused_Score', 'Structured_Score', 'Literature_Score', 'Evidence_Count', 'Strong_Evidence', 'Moderate_Evidence', 'Literature_Status', 'PubMed_PMIDs'];
  const rows = targets.map(t => [
    t.rank,
    `"${t.target_symbol}"`,
    `"${t.target_id}"`,
    `"${(t.target_name || '').replace(/"/g, '""')}"`,
    t.fused_score,
    t.structured_score,
    t.literature_score,
    t.evidence_count,
    t.strong_evidence_count,
    t.moderate_evidence_count,
    `"${t.literature_status}"`,
    `"${(t.papers_referenced || []).map(p => p.pmid).join(';')}"`
  ]);
  return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
}

function downloadFile(content, fileName, contentType) {
  const blob = new Blob([content], { type: contentType });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

// =========================================================================
// NATURAL COMPOUNDS & VERIFICATION TAB (STEPS 6 & 7)
// =========================================================================

let currentCompounds = null;
let allCompoundCards = [];

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('fetchCompoundsBtn').addEventListener('click', async () => {
    if (!currentResults) return;
    await fetchNaturalCompounds();
  });

  document.getElementById('compoundFilterInput').addEventListener('input', (e) => {
    filterCompounds(e.target.value);
  });

  document.getElementById('compoundSortSelect').addEventListener('change', (e) => {
    sortAndRenderCompounds(e.target.value);
  });

  document.getElementById('downloadCompoundsCsvBtn').addEventListener('click', () => {
    if (!currentCompounds) return;
    const csv = compoundsToCSV(currentCompounds.compounds);
    const slug = slugify(currentCompounds.disease_name || 'disease');
    downloadFile(csv, `${slug}_natural_compounds_verified.csv`, 'text/csv');
  });
});

async function fetchNaturalCompounds() {
  if (!currentResults) return;

  const idleState   = document.getElementById('compoundsIdleState');
  const loadingState = document.getElementById('compoundsLoadingState');
  const toolbar     = document.getElementById('compoundsToolbar');
  const summaryStrip = document.getElementById('compoundsSummaryStrip');
  const list        = document.getElementById('compoundsList');
  const fetchBtn    = document.getElementById('fetchCompoundsBtn');
  const loadingTxt  = document.getElementById('compoundsLoadingText');

  const disease  = currentResults.disease.canonical_name || currentResults.disease.input;
  const synonyms = currentResults.disease.synonyms || [];
  const targets  = (currentResults.targets || []).slice(0, 10).map(t => ({
    symbol: t.target_symbol,
    name:   t.target_name,
  }));

  idleState.style.display   = 'none';
  summaryStrip.style.display = 'none';
  toolbar.style.display      = 'none';
  list.innerHTML             = '';
  loadingState.style.display = 'flex';
  fetchBtn.disabled          = true;

  const loadingMessages = [
    'Searching PubMed for natural compounds associated with this disease…',
    'Querying ChEMBL bioactivity database for target protein assays…',
    'Extracting chemical candidates from literature abstracts…',
    'Resolving PubChem CIDs, Standard InChIKeys & Canonical SMILES…',
    'Verifying natural-origin status against phytochemical registries…',
    'Distinguishing natural vs. synthetic entities and retaining audit trail…',
  ];
  let msgIdx = 0;
  const msgInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % loadingMessages.length;
    if (loadingTxt) loadingTxt.textContent = loadingMessages[msgIdx];
  }, 3000);

  try {
    const resp = await fetch('/api/compounds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disease, targets, synonyms }),
    });

    clearInterval(msgInterval);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.message || 'Compound retrieval and verification failed');
    }

    const data = await resp.json();
    currentCompounds = data;

    loadingState.style.display = 'none';
    renderCompounds(data);
    fetchBtn.disabled = false;

    const metricCard = document.getElementById('compoundsMetricCard');
    if (metricCard) metricCard.style.display = '';
    const totalEl = document.getElementById('resTotalCompounds');
    if (totalEl) totalEl.textContent = data.total_compounds;
    const dualEl = document.getElementById('resDualRouteCount');
    if (dualEl) dualEl.textContent = `${data.dual_route_count} dual-route hits`;
    const tabCount = document.getElementById('tabCompoundsCount');
    if (tabCount) tabCount.textContent = data.total_compounds;

  } catch (err) {
    clearInterval(msgInterval);
    loadingState.style.display = 'none';
    idleState.style.display    = 'flex';
    fetchBtn.disabled          = false;
    alert(`Compound retrieval error: ${err.message}`);
  }
}

function renderCompounds(data) {
  const summaryStrip = document.getElementById('compoundsSummaryStrip');
  const toolbar      = document.getElementById('compoundsToolbar');
  const list         = document.getElementById('compoundsList');

  // Summary stats
  document.getElementById('cpStatTotalNum').textContent = data.total_compounds;
  document.getElementById('cpStatDualNum').textContent  = data.dual_route_count;
  document.getElementById('cpStatRouteA').textContent   = data.route_a_count;
  document.getElementById('cpStatRouteB').textContent   = data.route_b_count;

  const verifiedEl = document.getElementById('cpStatVerifiedNum');
  if (verifiedEl) verifiedEl.textContent = data.verified_natural_count || 0;

  summaryStrip.style.display = 'flex';
  toolbar.style.display      = 'flex';

  allCompoundCards = (data.compounds || []).map(c => buildCompoundCard(c));
  list.innerHTML = '';
  allCompoundCards.forEach(card => list.appendChild(card));
}

function buildCompoundCard(c) {
  const card = document.createElement('div');
  card.className = 'compound-card' + (c.is_dual_route ? ' dual-route' : '');
  card.dataset.name    = c.name;
  card.dataset.targets = (c.targets_targeted || []).join(' ').toLowerCase();
  card.dataset.routes  = (c.retrieval_routes || []).join(' ');
  card.dataset.cid     = c.pubchem_cid || '';
  card.dataset.class   = (c.natural_product_class || '').toLowerCase();

  // Route badges
  const routeMap = {
    disease_natural_literature: ['route-a', '🔵 Route A (Disease→Literature)'],
    protein_chembl_bioactivity: ['route-b-chembl', '🟡 Route B (Protein→ChEMBL)'],
    protein_literature:         ['route-b-lit',    '🟢 Route B (Protein→Literature)'],
  };
  const routeBadgesHtml = (c.retrieval_routes || []).map(r => {
    const [cls, label] = routeMap[r] || ['', r];
    return `<span class="route-badge ${cls}">${escapeHtml(label)}</span>`;
  }).join('');

  // Step 7 Origin Badge
  const originStatus = c.natural_origin_status || (c.natural_origin ? 'natural' : 'synthetic');
  let originClass = 'unverified';
  let originIcon = '❓';
  let originText = 'Origin Unverified';

  if (originStatus === 'natural') {
    originClass = 'natural';
    originIcon = '🌿';
    originText = c.natural_product_class ? `Verified Natural · ${c.natural_product_class}` : 'Verified Natural';
  } else if (originStatus === 'natural_derivative') {
    originClass = 'natural_derivative';
    originIcon = '🧪';
    originText = c.natural_product_class ? `Natural Derivative · ${c.natural_product_class}` : 'Natural Derivative';
  } else if (originStatus === 'synthetic') {
    originClass = 'synthetic';
    originIcon = '💊';
    originText = c.subclass ? `Synthetic · ${c.subclass}` : 'Synthetic Entity';
  }

  const originBadgeHtml = `<span class="origin-badge ${originClass}">${originIcon} ${escapeHtml(originText)}</span>`;

  // Target tags
  const targetTagsHtml = (c.targets_targeted || []).map(t =>
    `<span class="target-tag">${escapeHtml(t)}</span>`
  ).join('');

  // Detail chips
  const citationsHtml = c.citation_count
    ? `<span class="compound-detail-chip">📚 <strong>${c.citation_count}</strong> citations</span>` : '';
  const potencyHtml = c.best_bioactivity_nM != null
    ? `<span class="compound-detail-chip">⚗️ Best: <strong>${formatPotency(c.best_bioactivity_nM)}</strong></span>` : '';
  const formulaHtml = c.molecular_formula
    ? `<span class="compound-detail-chip">🧪 <strong>${escapeHtml(c.molecular_formula)}</strong></span>` : '';
  const mwHtml = c.molecular_weight
    ? `<span class="compound-detail-chip">⚖️ ${Number(c.molecular_weight).toFixed(1)} g/mol</span>` : '';

  // Chemical Identity Links
  const pubchemHtml = c.pubchem_cid
    ? `<a href="https://pubchem.ncbi.nlm.nih.gov/compound/${c.pubchem_cid}" target="_blank" rel="noopener" class="compound-pmid-link pubchem-link">PubChem: CID ${c.pubchem_cid} ↗</a>` : '';
  const chemblHtml = c.chembl_id && !c.chembl_id.startsWith('LIT:') && !c.chembl_id.startsWith('CID:')
    ? `<a href="https://www.ebi.ac.uk/chembl/compound_report_card/${c.chembl_id}/" target="_blank" rel="noopener" class="compound-pmid-link">ChEMBL: ${escapeHtml(c.chembl_id)} ↗</a>` : '';

  // InChIKey & SMILES copy chips
  const inchikeyHtml = c.inchikey
    ? `<span class="identity-chip" title="Click to copy InChIKey: ${escapeHtml(c.inchikey)}" onclick="navigator.clipboard.writeText('${escapeHtml(c.inchikey)}'); alert('Copied InChIKey to clipboard: ${escapeHtml(c.inchikey)}');">🔑 ${escapeHtml(c.inchikey.slice(0, 14))}… <small>(copy)</small></span>` : '';
  
  const smilesVal = c.canonical_smiles || c.smiles;
  const smilesHtml = smilesVal
    ? `<span class="identity-chip" title="Click to copy Canonical SMILES: ${escapeHtml(smilesVal)}" onclick="navigator.clipboard.writeText('${escapeHtml(smilesVal)}'); alert('Copied SMILES to clipboard!');">🧬 SMILES <small>(copy)</small></span>` : '';

  // Snippets (top 2)
  const snippets = c.provenance && c.provenance.snippets ? c.provenance.snippets.slice(0, 2) : [];
  const snippetsHtml = snippets.length
    ? `<div class="compound-snippets">${snippets.map(s => `<div class="compound-snippet">"${escapeHtml(s)}"</div>`).join('')}</div>` : '';

  // PMIDs
  const pmids = c.provenance && c.provenance.pmids ? c.provenance.pmids.slice(0, 5) : [];
  const pmidsHtml = pmids.length
    ? `<div class="compound-pmids-row">${pmids.map(p => `<a class="compound-pmid-link" href="https://pubmed.ncbi.nlm.nih.gov/${escapeHtml(p)}/" target="_blank" rel="noopener">PMID: ${escapeHtml(p)} ↗</a>`).join('')}</div>` : '';

  // Potency bar
  let potencyBarHtml = '';
  if (c.best_bioactivity_nM != null) {
    const pct = Math.min(100, Math.max(2, 100 - Math.log10(c.best_bioactivity_nM + 1) * 20));
    potencyBarHtml = `
      <div class="potency-bar-wrapper">
        <span class="potency-bar-label">Potency score (lower nM = better)</span>
        <div class="potency-bar-track"><div class="potency-bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
      </div>`;
  }

  // IUPAC Name
  const iupacHtml = c.iupac_name
    ? `<div style="font-size: 0.73rem; color: var(--text-dim); line-height: 1.35;"><strong>IUPAC:</strong> ${escapeHtml(c.iupac_name)}</div>`
    : '';

  card.innerHTML = `
    <div class="compound-card-header">
      <span class="compound-name">${escapeHtml(c.name)}</span>
      <div style="display: flex; gap: 6px; align-items: center;">
        ${originBadgeHtml}
        ${c.is_dual_route ? '<span class="dual-badge">⭐ Dual-Route</span>' : ''}
      </div>
    </div>

    <div class="compound-routes-row">${routeBadgesHtml}</div>

    <div class="compound-details-row">
      ${formulaHtml}${mwHtml}${citationsHtml}${potencyHtml}
    </div>

    ${(inchikeyHtml || smilesHtml) ? `
    <div class="compound-identity-row">
      ${inchikeyHtml}${smilesHtml}
    </div>` : ''}

    ${iupacHtml}

    ${targetTagsHtml ? `
    <div class="compound-targets-section">
      <span class="compound-targets-label">Active against targets</span>
      <div class="compound-target-tags">${targetTagsHtml}</div>
    </div>` : ''}

    ${potencyBarHtml}

    ${snippetsHtml}

    ${(pmids.length || chemblHtml || pubchemHtml) ? `
    <div class="compound-pmids-row">
      ${pubchemHtml}${chemblHtml}${pmidsHtml ? pmidsHtml : ''}
    </div>` : ''}
  `;

  return card;
}

function formatPotency(nM) {
  if (nM == null) return '—';
  if (nM < 1) return `${(nM * 1000).toFixed(0)} pM`;
  if (nM < 1000) return `${nM.toFixed(1)} nM`;
  return `${(nM / 1000).toFixed(2)} µM`;
}

function filterCompounds(query) {
  const q = (query || '').toLowerCase();
  const list = document.getElementById('compoundsList');
  list.innerHTML = '';
  const filtered = allCompoundCards.filter(card => {
    const text = (
      (card.dataset.name || '') + ' ' +
      (card.dataset.targets || '') + ' ' +
      (card.dataset.routes || '') + ' ' +
      (card.dataset.cid || '') + ' ' +
      (card.dataset.class || '') + ' ' +
      (card.textContent || '')
    ).toLowerCase();
    return text.includes(q);
  });
  filtered.forEach(card => list.appendChild(card));
}

function sortAndRenderCompounds(mode) {
  if (!currentCompounds) return;
  const compounds = [...(currentCompounds.compounds || [])];
  if (mode === 'name') {
    compounds.sort((a, b) => a.name.localeCompare(b.name));
  } else if (mode === 'citations') {
    compounds.sort((a, b) => (b.citation_count || 0) - (a.citation_count || 0));
  } else if (mode === 'potency') {
    compounds.sort((a, b) => {
      const av = a.best_bioactivity_nM ?? Infinity;
      const bv = b.best_bioactivity_nM ?? Infinity;
      return av - bv;
    });
  } else {
    // default: dual first, then natural
    compounds.sort((a, b) => {
      if (a.is_dual_route && !b.is_dual_route) return -1;
      if (!a.is_dual_route && b.is_dual_route) return 1;
      return (b.citation_count || 0) - (a.citation_count || 0);
    });
  }
  allCompoundCards = compounds.map(c => buildCompoundCard(c));
  const list = document.getElementById('compoundsList');
  list.innerHTML = '';
  allCompoundCards.forEach(card => list.appendChild(card));
}

function compoundsToCSV(compounds) {
  const headers = ['Name', 'PubChem_CID', 'InChIKey', 'Formula', 'Molecular_Weight', 'Origin_Status', 'Phytochemical_Class', 'ChEMBL_ID', 'Natural_Origin', 'Retrieval_Routes', 'Targets', 'Citations', 'Best_Potency_nM', 'Dual_Route', 'PMIDs'];
  const rows = (compounds || []).map(c => [
    `"${(c.name || '').replace(/"/g, '""')}"`,
    c.pubchem_cid || '',
    `"${c.inchikey || ''}"`,
    `"${c.molecular_formula || ''}"`,
    c.molecular_weight != null ? c.molecular_weight : '',
    `"${c.natural_origin_status || ''}"`,
    `"${c.natural_product_class || ''}"`,
    `"${c.chembl_id || ''}"`,
    c.natural_origin ? 'Yes' : 'No',
    `"${(c.retrieval_routes || []).join(';')}"`,
    `"${(c.targets_targeted || []).join(';')}"`,
    c.citation_count || 0,
    c.best_bioactivity_nM != null ? c.best_bioactivity_nM.toFixed(2) : '',
    c.is_dual_route ? 'Yes' : 'No',
    `"${((c.provenance && c.provenance.pmids) || []).join(';')}"`,
  ]);
  return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
}
