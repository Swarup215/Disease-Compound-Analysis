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
    // Optionally balance literature weight
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

  // Quick disease tags
  quickTags.forEach(tag => {
    tag.addEventListener('click', () => {
      diseaseInput.value = tag.getAttribute('data-disease');
      diseaseInput.focus();
    });
  });

  clearDiseaseBtn.addEventListener('click', () => {
    diseaseInput.value = '';
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

  // Step simulation intervals for smooth feedback while server computes
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
      const err = await response.json();
      throw new Error(err.message || 'Pipeline analysis failed');
    }

    const data = await response.json();
    currentResults = data;

    // Finish progress
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
      // Scroll to results
      resultsSection.scrollIntoView({ behavior: 'smooth' });
    }, 450);

  } catch (err) {
    clearInterval(progressInterval);
    progressStageText.textContent = `Error: ${err.message}`;
    runPipelineBtn.disabled = false;
    runPipelineBtn.style.opacity = '1';
    alert(`Pipeline error: ${err.message}`);
  }
}

function renderResults(data) {
  const disease = data.disease || {};
  const metrics = data.metrics || {};
  const targets = data.targets || [];
  const papers = data.papers || [];
  const graph = data.graph || {};

  // Overview metrics
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

  // Disease ID badges
  const badgesContainer = document.getElementById('resDiseaseBadges');
  badgesContainer.innerHTML = '';
  const ids = disease.identifiers || {};
  if (ids.mondo) badgesContainer.appendChild(createBadge('MONDO: ' + ids.mondo, 'badge-mono'));
  if (ids.efo) badgesContainer.appendChild(createBadge('EFO: ' + ids.efo, 'badge-mono'));
  if (ids.doid) badgesContainer.appendChild(createBadge('DOID: ' + ids.doid, 'badge-mono'));
  if (ids.mesh) badgesContainer.appendChild(createBadge('MeSH: ' + ids.mesh, 'badge-mono'));

  // Render Target Cards
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

    // Generate evidence items HTML (Where evidence is found)
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
        <!-- Rank -->
        <div class="target-rank-col">
          <div class="${rankClass}">#${target.rank}</div>
        </div>

        <!-- Target Info -->
        <div class="target-info-col">
          <h4>
            <span>${escapeHtml(target.target_symbol)}</span>
            <span class="badge badge-mono">${escapeHtml(target.target_id)}</span>
          </h4>
          <p class="target-full-name" title="${escapeHtml(target.target_name)}">${escapeHtml(target.target_name)}</p>
        </div>

        <!-- Fused Score -->
        <div class="target-score-col">
          <span class="score-title">Fused Score</span>
          <span class="score-num">${(target.fused_score * 100).toFixed(1)}%</span>
          <div class="score-bar-mini">
            <div class="score-bar-fill" style="width: ${target.fused_score * 100}%;"></div>
          </div>
        </div>

        <!-- Score Breakdown -->
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

        <!-- Evidence Pill -->
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

        <!-- Expand Button -->
        <div class="target-expand-col">
          <button type="button" class="expand-toggle-btn" title="View where literature evidence is found">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>
        </div>
      </div>

      <!-- Expandable Evidence Drawer (Where evidence is found) -->
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

    // Toggle expand
    const btn = card.querySelector('.expand-toggle-btn');
    const drawer = card.querySelector('.evidence-drawer');
    btn.addEventListener('click', () => {
      const isOpen = drawer.classList.contains('open');
      drawer.classList.toggle('open', !isOpen);
      btn.classList.toggle('expanded', !isOpen);
    });

    targetsList.appendChild(card);
  });

  // Render Papers Tab
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

  // Render Graph Tab Stats & Edges
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

  // Raw JSON
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
