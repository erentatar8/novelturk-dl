// Modern Web Front-end Controller for PyWebView

// State
const state = {
  novel: null,
  chapters: [],
  selectedIds: new Set(),
  options: {
    format_epub: true,
    format_pdf: true,
    do_split: true,
    split_size: 300,
    concurrency: 4,
    custom_cover_path: null,
    only_numbered_titles: false,
    output_dir: ""
  },
  isRunning: false
};

// DOM Elements
const el = {
  novelUrlInput: document.getElementById('novelUrlInput'),
  btnLoadNovel: document.getElementById('btnLoadNovel'),
  btnOpenSettings: document.getElementById('btnOpenSettings'),
  novelCoverImg: document.getElementById('novelCoverImg'),
  novelCoverPlaceholder: document.getElementById('novelCoverPlaceholder'),
  btnEditCover: document.getElementById('btnEditCover'),
  btnResetCover: document.getElementById('btnResetCover'),
  novelTitle: document.getElementById('novelTitle'),
  novelAuthor: document.getElementById('novelAuthor'),
  novelBadges: document.getElementById('novelBadges'),
  statTotalChapters: document.getElementById('statTotalChapters'),
  statDownloadedChapters: document.getElementById('statDownloadedChapters'),
  statSelectedChapters: document.getElementById('statSelectedChapters'),
  statPercent: document.getElementById('statPercent'),
  summaryFormat: document.getElementById('summaryFormat'),
  summarySplit: document.getElementById('summarySplit'),
  summaryConcurrency: document.getElementById('summaryConcurrency'),
  btnStartProcess: document.getElementById('btnStartProcess'),
  btnStopProcess: document.getElementById('btnStopProcess'),
  btnOpenFolder: document.getElementById('btnOpenFolder'),
  btnSelectAll: document.getElementById('btnSelectAll'),
  btnSelectNone: document.getElementById('btnSelectNone'),
  btnSelectMissing: document.getElementById('btnSelectMissing'),
  btnSelectInvert: document.getElementById('btnSelectInvert'),
  quickRangeChips: document.getElementById('quickRangeChips'),
  rangeStart: document.getElementById('rangeStart'),
  rangeEnd: document.getElementById('rangeEnd'),
  btnApplyRange: document.getElementById('btnApplyRange'),
  tableSearchInput: document.getElementById('tableSearchInput'),
  chkMasterTable: document.getElementById('chkMasterTable'),
  chapterTableBody: document.getElementById('chapterTableBody'),
  terminalBody: document.getElementById('terminalBody'),
  btnClearLog: document.getElementById('btnClearLog'),
  progressBarFill: document.getElementById('progressBarFill'),
  statusLabel: document.getElementById('statusLabel'),
  // Modal Elements
  settingsModal: document.getElementById('settingsModal'),
  btnCloseSettings: document.getElementById('btnCloseSettings'),
  btnSaveSettings: document.getElementById('btnSaveSettings'),
  chkFormatEpub: document.getElementById('chkFormatEpub'),
  chkFormatPdf: document.getElementById('chkFormatPdf'),
  rbSplitYes: document.getElementById('rbSplitYes'),
  rbSplitNo: document.getElementById('rbSplitNo'),
  splitSizeInput: document.getElementById('splitSizeInput'),
  concurrencyRange: document.getElementById('concurrencyRange'),
  concurrencyValue: document.getElementById('concurrencyValue'),
  rbCoverAuto: document.getElementById('rbCoverAuto'),
  rbCoverCustom: document.getElementById('rbCoverCustom'),
  customCoverBox: document.getElementById('customCoverBox'),
  customCoverPath: document.getElementById('customCoverPath'),
  btnBrowseCover: document.getElementById('btnBrowseCover'),
  rbTitleFull: document.getElementById('rbTitleFull'),
  rbTitleNum: document.getElementById('rbTitleNum'),
  outputDirPath: document.getElementById('outputDirPath'),
  btnBrowseOutputDir: document.getElementById('btnBrowseOutputDir')
};

// Logging Utility
function appendLog(message, level = 'info') {
  const line = document.createElement('div');
  line.className = `terminal-line ${level}`;
  line.textContent = message;
  el.terminalBody.appendChild(line);
  el.terminalBody.scrollTop = el.terminalBody.scrollHeight;
}

// Global Callback Hooks for Python WebApi
window.onLogReceived = (msg, level) => {
  appendLog(msg, level);
};

window.onProgressUpdated = (current, total, text) => {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  el.progressBarFill.style.width = `${pct}%`;
  el.statusLabel.textContent = `${text} (%${pct})`;
};

window.onChapterStatusUpdated = (chId, status) => {
  const badge = document.getElementById(`status-badge-${chId}`);
  if (badge) {
    badge.textContent = status;
    badge.className = 'status-pill downloaded';
  }
  const ch = state.chapters.find(c => c.id === chId);
  if (ch) ch.is_downloaded = true;
};

window.onStatsUpdated = (downloaded, total, percent) => {
  el.statDownloadedChapters.textContent = downloaded;
  el.statPercent.textContent = `%${percent.toFixed(1)}`;
};

window.onProcessFinished = (success, message, outputDir) => {
  state.isRunning = false;
  el.btnStartProcess.disabled = false;
  el.btnStopProcess.disabled = true;
  el.btnLoadNovel.disabled = false;

  if (success) {
    el.statusLabel.textContent = "Tamamlandı!";
    appendLog("🎉 " + message, "success");
    if (outputDir) {
      state.lastOutputDir = outputDir;
    }
  } else {
    el.statusLabel.textContent = "İşlem durduruldu / Hata oluştu.";
    appendLog("⚠️ " + message, "warning");
  }
};

// Cover display helper
function updateCoverDisplay() {
  const customPath = state.options.custom_cover_path;
  const originalUrl = state.novel ? state.novel.cover_url : null;

  if (customPath && state.customCoverDataUri) {
    el.novelCoverImg.src = state.customCoverDataUri;
    el.novelCoverImg.style.display = 'block';
    el.novelCoverPlaceholder.style.display = 'none';
    el.btnResetCover.style.display = 'flex';
    el.btnEditCover.title = 'Özel Kapağı Değiştir';
  } else if (originalUrl) {
    el.novelCoverImg.src = originalUrl;
    el.novelCoverImg.style.display = 'block';
    el.novelCoverPlaceholder.style.display = 'none';
    el.btnResetCover.style.display = 'none';
    el.btnEditCover.title = 'Özel Kapak Resmi Seç';
  } else {
    el.novelCoverImg.style.display = 'none';
    el.novelCoverPlaceholder.style.display = 'flex';
    el.btnResetCover.style.display = 'none';
    el.btnEditCover.title = 'Özel Kapak Resmi Seç';
  }
}

// UI Rendering
function renderNovelInfo(novel) {
  state.novel = novel;
  el.novelTitle.textContent = novel.title;
  el.novelAuthor.textContent = `Yazar: ${novel.author}`;
  
  updateCoverDisplay();

  el.novelBadges.innerHTML = '';
  if (novel.genres && novel.genres.length > 0) {
    novel.genres.slice(0, 3).forEach(g => {
      const b = document.createElement('span');
      b.className = 'badge';
      b.textContent = g;
      el.novelBadges.appendChild(b);
    });
  }
  const totalB = document.createElement('span');
  totalB.className = 'badge badge-green';
  totalB.textContent = `${novel.total_chapters} Bölüm`;
  el.novelBadges.appendChild(totalB);

  el.statTotalChapters.textContent = novel.total_chapters;
  el.statDownloadedChapters.textContent = novel.downloaded_count;
  el.statPercent.textContent = `%${novel.percent.toFixed(1)}`;

  if (!state.options.output_dir) {
    state.options.output_dir = novel.default_output_dir;
    el.outputDirPath.value = novel.default_output_dir;
  }

  renderQuickRangeChips(novel.total_chapters);
}

function renderQuickRangeChips(total) {
  el.quickRangeChips.innerHTML = '';
  if (total <= 300) return;

  const step = 300;
  const count = Math.ceil(total / step);
  for (let i = 0; i < count; i++) {
    const s = i * step + 1;
    const e = Math.min((i + 1) * step, total);
    const chip = document.createElement('button');
    chip.className = 'chip-btn';
    chip.textContent = `${s}-${e}`;
    chip.title = `Bölüm ${s} ile ${e} arasını seç`;
    chip.addEventListener('click', () => selectRange(s, e));
    el.quickRangeChips.appendChild(chip);
  }
}

function renderTable() {
  const searchTerm = el.tableSearchInput.value.toLowerCase().trim();
  const frag = document.createDocumentFragment();

  const filtered = state.chapters.filter(ch => {
    if (!searchTerm) return true;
    return ch.title.toLowerCase().includes(searchTerm) || String(ch.order_index).includes(searchTerm);
  });

  if (filtered.length === 0) {
    el.chapterTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:40px 0; color:var(--text-dim);">Eşleşen bölüm bulunamadı.</td></tr>`;
    return;
  }

  filtered.forEach(ch => {
    const tr = document.createElement('tr');
    const isSelected = state.selectedIds.has(ch.id);
    if (isSelected) tr.classList.add('selected');

    tr.innerHTML = `
      <td style="text-align: center;">
        <input type="checkbox" class="ch-checkbox" data-id="${ch.id}" ${isSelected ? 'checked' : ''}>
      </td>
      <td style="font-weight: 600; color: var(--text-dim);">${ch.order_index}</td>
      <td style="font-weight: 500;">${escapeHtml(ch.title)}</td>
      <td>
        <span id="status-badge-${ch.id}" class="status-pill ${ch.is_downloaded ? 'downloaded' : 'pending'}">
          ${ch.is_downloaded ? '✓ İndi' : 'Bekliyor'}
        </span>
      </td>
    `;

    // Click row toggles checkbox
    tr.addEventListener('click', (e) => {
      if (e.target.tagName !== 'INPUT') {
        const cb = tr.querySelector('.ch-checkbox');
        cb.checked = !cb.checked;
        toggleChapterSelection(ch.id, cb.checked);
        tr.classList.toggle('selected', cb.checked);
      }
    });

    const checkbox = tr.querySelector('.ch-checkbox');
    checkbox.addEventListener('change', (e) => {
      toggleChapterSelection(ch.id, e.target.checked);
      tr.classList.toggle('selected', e.target.checked);
    });

    frag.appendChild(tr);
  });

  el.chapterTableBody.innerHTML = '';
  el.chapterTableBody.appendChild(frag);
  updateMasterCheckbox();
  updateSelectedStats();
}

function toggleChapterSelection(chId, checked) {
  if (checked) {
    state.selectedIds.add(chId);
  } else {
    state.selectedIds.delete(chId);
  }
  updateSelectedStats();
  updateMasterCheckbox();
}

function updateSelectedStats() {
  const count = state.selectedIds.size;
  el.statSelectedChapters.textContent = count;
  el.btnStartProcess.disabled = count === 0 || state.isRunning;
}

function updateMasterCheckbox() {
  if (state.chapters.length === 0) {
    el.chkMasterTable.checked = false;
    el.chkMasterTable.indeterminate = false;
    return;
  }
  if (state.selectedIds.size === state.chapters.length) {
    el.chkMasterTable.checked = true;
    el.chkMasterTable.indeterminate = false;
  } else if (state.selectedIds.size > 0) {
    el.chkMasterTable.checked = false;
    el.chkMasterTable.indeterminate = true;
  } else {
    el.chkMasterTable.checked = false;
    el.chkMasterTable.indeterminate = false;
  }
}

function selectAll() {
  state.chapters.forEach(ch => state.selectedIds.add(ch.id));
  renderTable();
}

function selectNone() {
  state.selectedIds.clear();
  renderTable();
}

function selectMissing() {
  state.selectedIds.clear();
  state.chapters.forEach(ch => {
    if (!ch.is_downloaded) state.selectedIds.add(ch.id);
  });
  renderTable();
}

function selectInvert() {
  state.chapters.forEach(ch => {
    if (state.selectedIds.has(ch.id)) {
      state.selectedIds.delete(ch.id);
    } else {
      state.selectedIds.add(ch.id);
    }
  });
  renderTable();
}

function selectRange(start, end) {
  state.selectedIds.clear();
  state.chapters.forEach(ch => {
    if (ch.order_index >= start && ch.order_index <= end) {
      state.selectedIds.add(ch.id);
    }
  });
  renderTable();
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// Update summary card in sidebar
function updateSummaryBadges() {
  const formats = [];
  if (state.options.format_epub) formats.push("EPUB");
  if (state.options.format_pdf) formats.push("PDF");
  el.summaryFormat.textContent = formats.length > 0 ? formats.join(" + ") : "Seçilmedi";

  if (state.options.do_split) {
    el.summarySplit.textContent = `${state.options.split_size}'lük Ciltler`;
  } else {
    el.summarySplit.textContent = "Tek Cilt (Tam)";
  }

  el.summaryConcurrency.textContent = `${state.options.concurrency} İş Parçacığı`;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  // Load novel action
  el.btnLoadNovel.addEventListener('click', async () => {
    const url = el.novelUrlInput.value.trim();
    if (!url) return;

    el.btnLoadNovel.disabled = true;
    el.btnLoadNovel.textContent = "Yükleniyor...";
    appendLog(`🔎 Novel sorgulanıyor: ${url}`);

    try {
      if (window.pywebview && window.pywebview.api) {
        const res = await window.pywebview.api.load_novel(url);
        if (res.success) {
          renderNovelInfo(res.novel);
          state.chapters = res.chapters;
          selectAll(); // Default: select all
        } else {
          alert("Hata: " + res.error);
        }
      } else {
        appendLog("⚠️ PyWebView API henüz hazır değil.", "warning");
      }
    } catch (e) {
      appendLog("❌ Hata: " + e, "error");
    } finally {
      el.btnLoadNovel.disabled = false;
      el.btnLoadNovel.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
        Fihristi Getir
      `;
    }
  });

  // Table Master Checkbox
  el.chkMasterTable.addEventListener('change', (e) => {
    if (e.target.checked) selectAll();
    else selectNone();
  });

  // Selection chips
  el.btnSelectAll.addEventListener('click', selectAll);
  el.btnSelectNone.addEventListener('click', selectNone);
  el.btnSelectMissing.addEventListener('click', selectMissing);
  el.btnSelectInvert.addEventListener('click', selectInvert);

  // Range button
  el.btnApplyRange.addEventListener('click', () => {
    const start = parseInt(el.rangeStart.value, 10);
    const end = parseInt(el.rangeEnd.value, 10);
    if (!isNaN(start) && !isNaN(end) && start <= end) {
      selectRange(start, end);
    } else {
      alert("Lütfen geçerli bir başlangıç ve bitiş aralığı girin.");
    }
  });

  // Search input
  el.tableSearchInput.addEventListener('input', () => {
    renderTable();
  });

  // Clear log
  el.btnClearLog.addEventListener('click', () => {
    el.terminalBody.innerHTML = '';
  });

  // Open Settings Modal
  el.btnOpenSettings.addEventListener('click', () => {
    el.chkFormatEpub.checked = state.options.format_epub;
    el.chkFormatPdf.checked = state.options.format_pdf;
    if (state.options.do_split) el.rbSplitYes.checked = true;
    else el.rbSplitNo.checked = true;
    el.splitSizeInput.value = state.options.split_size;
    el.concurrencyRange.value = state.options.concurrency;
    el.concurrencyValue.textContent = `${state.options.concurrency} İş Parçacığı`;
    
    if (state.options.custom_cover_path) {
      el.rbCoverCustom.checked = true;
      el.customCoverBox.style.display = 'flex';
      el.customCoverPath.value = state.options.custom_cover_path;
    } else {
      el.rbCoverAuto.checked = true;
      el.customCoverBox.style.display = 'none';
    }

    if (state.options.only_numbered_titles) el.rbTitleNum.checked = true;
    else el.rbTitleFull.checked = true;

    el.outputDirPath.value = state.options.output_dir;
    el.settingsModal.classList.add('open');
  });

  // Close Settings Modal
  el.btnCloseSettings.addEventListener('click', () => {
    el.settingsModal.classList.remove('open');
  });

  // Save Settings Modal
  el.btnSaveSettings.addEventListener('click', () => {
    state.options.format_epub = el.chkFormatEpub.checked;
    state.options.format_pdf = el.chkFormatPdf.checked;
    state.options.do_split = el.rbSplitYes.checked;
    state.options.split_size = parseInt(el.splitSizeInput.value, 10) || 300;
    state.options.concurrency = parseInt(el.concurrencyRange.value, 10) || 4;
    state.options.custom_cover_path = el.rbCoverCustom.checked ? el.customCoverPath.value : null;
    if (!state.options.custom_cover_path) {
      state.customCoverDataUri = null;
    }
    updateCoverDisplay();
    state.options.only_numbered_titles = el.rbTitleNum.checked;
    state.options.output_dir = el.outputDirPath.value;

    updateSummaryBadges();
    el.settingsModal.classList.remove('open');
    appendLog("⚙️ Ayarlar güncellendi.");
  });

  // Concurrency slider
  el.concurrencyRange.addEventListener('input', (e) => {
    el.concurrencyValue.textContent = `${e.target.value} İş Parçacığı`;
  });

  // Cover mode toggle
  el.rbCoverAuto.addEventListener('change', () => {
    el.customCoverBox.style.display = 'none';
  });
  el.rbCoverCustom.addEventListener('change', () => {
    el.customCoverBox.style.display = 'flex';
  });

  // Quick Cover Edit Button (on card)
  el.btnEditCover.addEventListener('click', async () => {
    if (window.pywebview && window.pywebview.api) {
      const path = await window.pywebview.api.browse_custom_cover();
      if (path) {
        state.options.custom_cover_path = path;
        el.customCoverPath.value = path;
        el.rbCoverCustom.checked = true;
        el.customCoverBox.style.display = 'flex';

        // Load preview immediately
        const dataUri = await window.pywebview.api.get_image_data_uri(path);
        if (dataUri) {
          state.customCoverDataUri = dataUri;
        }
        updateCoverDisplay();
        appendLog(`🖼️ Özel kapak seçildi: ${path}`);
      }
    }
  });

  // Quick Cover Reset Button (revert to novel original cover)
  el.btnResetCover.addEventListener('click', () => {
    state.options.custom_cover_path = null;
    state.customCoverDataUri = null;
    el.customCoverPath.value = '';
    el.rbCoverAuto.checked = true;
    el.customCoverBox.style.display = 'none';

    updateCoverDisplay();
    appendLog("🖼️ Orijinal kapak resmine geri dönüldü.");
  });

  // Browse cover (inside settings modal)
  el.btnBrowseCover.addEventListener('click', async () => {
    if (window.pywebview && window.pywebview.api) {
      const path = await window.pywebview.api.browse_custom_cover();
      if (path) {
        el.customCoverPath.value = path;
        state.options.custom_cover_path = path;
        const dataUri = await window.pywebview.api.get_image_data_uri(path);
        if (dataUri) {
          state.customCoverDataUri = dataUri;
        }
        updateCoverDisplay();
      }
    }
  });

  // Browse output dir
  el.btnBrowseOutputDir.addEventListener('click', async () => {
    if (window.pywebview && window.pywebview.api) {
      const path = await window.pywebview.api.browse_output_dir(el.outputDirPath.value);
      if (path) {
        el.outputDirPath.value = path;
      }
    }
  });

  // Open output folder in Finder
  el.btnOpenFolder.addEventListener('click', () => {
    const dir = state.lastOutputDir || state.options.output_dir;
    if (window.pywebview && window.pywebview.api && dir) {
      window.pywebview.api.open_folder(dir);
    }
  });

  // Start Process
  el.btnStartProcess.addEventListener('click', async () => {
    if (state.selectedIds.size === 0) {
      alert("Lütfen en az bir bölüm seçin.");
      return;
    }

    state.isRunning = true;
    el.btnStartProcess.disabled = true;
    el.btnStopProcess.disabled = false;
    el.btnLoadNovel.disabled = true;
    el.progressBarFill.style.width = '0%';
    el.statusLabel.textContent = "İşlem başlatılıyor...";

    const payload = {
      ...state.options,
      selected_chapter_ids: Array.from(state.selectedIds)
    };

    try {
      const res = await window.pywebview.api.start_process(payload);
      if (!res.success) {
        alert("Hata: " + res.error);
        state.isRunning = false;
        el.btnStartProcess.disabled = false;
        el.btnStopProcess.disabled = true;
        el.btnLoadNovel.disabled = false;
      }
    } catch (e) {
      appendLog("❌ Başlatma hatası: " + e, "error");
      state.isRunning = false;
      el.btnStartProcess.disabled = false;
      el.btnStopProcess.disabled = true;
      el.btnLoadNovel.disabled = false;
    }
  });

  // Stop Process
  el.btnStopProcess.addEventListener('click', async () => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.stop_process();
      el.btnStopProcess.disabled = true;
    }
  });

  updateSummaryBadges();
});

// Ready hook
window.addEventListener('pywebviewready', () => {
  appendLog("🚀 WebKit UI & PyWebView API bağlandı. Hazır.");
});
