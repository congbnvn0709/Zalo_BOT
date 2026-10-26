/**
 * Zalo Attendance Web Dashboard SPA Controller.
 * Zero-build Vanilla ES6+ Application Logic.
 */

// Global Application State
const state = {
  records: [],
  currentFilter: 'ALL',
  templateInfo: null,
  useCustomTemplate: false,
  isParsing: false,
  isExporting: false,
};

// ==============================================================================
// Utility Functions
// ==============================================================================

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function updateMessageCounter() {
  const textarea = document.getElementById('zalo-raw-text');
  const counter = document.getElementById('text-counter');
  if (!textarea || !counter) return;

  const text = textarea.value.trim();
  if (!text) {
    counter.textContent = '0 tin nhắn nhận diện';
    return;
  }

  // Count headers or blank block separators
  const matches = text.match(/(?:HỌ\s*TÊN|HO\s*TEN)\s*[:：]/gi);
  const count = matches ? matches.length : 1;
  counter.textContent = `${count} tin nhắn nhận diện`;
}

// ==============================================================================
// API Communications
// ==============================================================================

async function fetchTemplateInfo() {
  try {
    const res = await fetch('/api/template/info');
    if (!res.ok) throw new Error('Không thể tải thông tin file mẫu.');
    const data = await res.json();
    state.templateInfo = data;

    document.getElementById('tpl-sheet-name').textContent = data.sheet_name || 'BẢNG CHẤM CÔNG';
    document.getElementById('tpl-employees-count').textContent = `${data.total_employees || data.employees.length} nhân viên`;
    if (data.date_range && data.date_range.length === 2 && data.date_range[0]) {
      document.getElementById('tpl-date-range').textContent = `${data.date_range[0]} → ${data.date_range[1]}`;
    } else {
      document.getElementById('tpl-date-range').textContent = 'Tự động theo sheet';
    }
  } catch (err) {
    console.warn('Lỗi khi tải metadata template:', err);
    document.getElementById('tpl-sheet-name').textContent = 'BẢNG CHẤM CÔNG WEVN - ETS';
  }
}

async function loadSample() {
  try {
    const res = await fetch('/api/sample');
    if (res.ok) {
      const data = await res.json();
      const textarea = document.getElementById('zalo-raw-text');
      textarea.value = data.sample_text;
      updateMessageCounter();
    }
  } catch (err) {
    console.error('Lỗi khi tải dữ liệu mẫu:', err);
  }
}

async function handleParse() {
  const textarea = document.getElementById('zalo-raw-text');
  const text = textarea.value.trim();
  if (!text) {
    alert('Vui lòng dán tin nhắn Zalo trước khi bóc tách.');
    textarea.focus();
    return;
  }

  const btn = document.getElementById('btn-parse');
  const spinner = document.getElementById('parse-spinner');
  const icon = document.getElementById('parse-icon');

  state.isParsing = true;
  btn.disabled = true;
  spinner.classList.remove('hidden');
  icon.classList.add('hidden');

  try {
    const res = await fetch('/api/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Lỗi bóc tách tin nhắn.');
    }

    const data = await res.json();
    state.records = data.records || [];
    renderTable();
    updateSummaryBadges(data.summary);
  } catch (err) {
    alert('Lỗi: ' + err.message);
  } finally {
    state.isParsing = false;
    btn.disabled = false;
    spinner.classList.add('hidden');
    icon.classList.remove('hidden');
  }
}

async function handleTemplateUpload(file) {
  if (!file) return;
  const feedback = document.getElementById('upload-feedback');
  feedback.textContent = 'Đang tải lên và phân tích...';
  feedback.className = 'text-[11px] text-indigo-600 mt-1';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/template/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Lỗi tải file mẫu.');
    }

    const data = await res.json();
    state.templateInfo = data;
    state.useCustomTemplate = true;

    feedback.textContent = `✓ Đã kích hoạt mẫu: ${data.sheet_name} (${data.total_employees} NV)`;
    feedback.className = 'text-[11px] text-emerald-600 font-medium mt-1';

    document.getElementById('tpl-sheet-name').textContent = data.sheet_name;
    document.getElementById('tpl-employees-count').textContent = `${data.total_employees} nhân viên`;
    if (data.date_range && data.date_range[0]) {
      document.getElementById('tpl-date-range').textContent = `${data.date_range[0]} → ${data.date_range[1]}`;
    }
  } catch (err) {
    feedback.textContent = `✕ Lỗi: ${err.message}`;
    feedback.className = 'text-[11px] text-rose-600 font-medium mt-1';
  }
}

async function handleExportExcel() {
  if (state.records.length === 0) {
    alert('Không có bản ghi nào để xuất file Excel. Vui lòng bóc tách tin nhắn trước.');
    return;
  }

  const btn = document.getElementById('btn-export');
  const spinner = document.getElementById('export-spinner');
  const icon = document.getElementById('export-icon');
  const filenameInput = document.getElementById('export-filename');

  state.isExporting = true;
  btn.disabled = true;
  spinner.classList.remove('hidden');
  icon.classList.add('hidden');

  try {
    const res = await fetch('/api/export-excel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        records: state.records,
        use_custom_template: state.useCustomTemplate,
        output_filename: filenameInput.value.trim() || 'BANG_CHAM_CONG_CAP_NHAT.xlsx'
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Lỗi xuất file Excel.');
    }

    const data = await res.json();
    renderExportBanner(data);
  } catch (err) {
    alert('Lỗi xuất file: ' + err.message);
  } finally {
    state.isExporting = false;
    btn.disabled = false;
    spinner.classList.add('hidden');
    icon.classList.remove('hidden');
  }
}

// ==============================================================================
// UI Rendering & Table Operations
// ==============================================================================

function renderTable() {
  const tbody = document.getElementById('table-body');
  if (!tbody) return;

  const filtered = state.records.filter(r => {
    if (state.currentFilter === 'ALL') return true;
    return r.status === state.currentFilter;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr id="empty-row">
        <td colspan="10" class="px-6 py-12 text-center text-slate-400">
          ${state.records.length === 0 
            ? 'Chưa có dữ liệu. Vui lòng dán tin nhắn Zalo ở Bước 1 và nhấn "Bóc tách dữ liệu".' 
            : 'Không có bản ghi nào phù hợp với bộ lọc hiện tại.'}
        </td>
      </tr>
    `;
    return;
  }

  let html = '';
  filtered.forEach((rec, index) => {
    const h = rec.hours || {};
    const hcn = h.hcn_100 || 0;
    const tcn = h.tcn_150 || 0;
    const night = (h.hcd_130 || 0) + (h.tcd_195 || 0) + (h.sunday_night_260 || 0);
    const meal = rec.meal_count !== undefined ? rec.meal_count : (rec.meals || 0);

    let badgeClass = 'badge-valid';
    let statusLabel = 'Hợp lệ';
    if (rec.status === 'WARNING') {
      badgeClass = 'badge-warning';
      statusLabel = 'Cần chú ý';
    } else if (rec.status === 'ERROR') {
      badgeClass = 'badge-error';
      statusLabel = 'Lỗi';
    }

    const shiftDisplay = (rec.shift_type === 'NIGHT' || rec.shift === 'Ca đêm') ? 'Ca đêm' : 'Ca ngày';

    html += `
      <tr data-id="${escapeHtml(rec.id)}" class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="px-3 py-2.5 text-center font-mono text-slate-500">${index + 1}</td>
        
        <!-- Editable Name -->
        <td class="px-4 py-2.5 font-medium text-slate-900">
          <div class="editable-cell" data-field="employee_name">
            <span>${escapeHtml(rec.employee_name || 'Chưa rõ')}</span>
          </div>
        </td>

        <!-- Editable Date -->
        <td class="px-3 py-2.5 text-center">
          <div class="editable-cell" data-field="date_str">
            <span class="font-mono text-slate-700">${escapeHtml(rec.date_str || rec.resolved_date || '-')}</span>
          </div>
        </td>

        <!-- Editable Shift -->
        <td class="px-3 py-2.5 text-center">
          <span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium ${shiftDisplay === 'Ca đêm' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}">
            ${shiftDisplay}
          </span>
        </td>

        <!-- Editable HCN -->
        <td class="px-3 py-2.5 text-center">
          <div class="editable-cell" data-field="hcn_100">
            <span class="font-mono font-semibold text-slate-800">${hcn}</span>
          </div>
        </td>

        <!-- Editable TCN -->
        <td class="px-3 py-2.5 text-center">
          <div class="editable-cell" data-field="tcn_150">
            <span class="font-mono ${tcn > 0 ? 'text-amber-600 font-bold' : 'text-slate-400'}">${tcn}</span>
          </div>
        </td>

        <!-- Editable Night -->
        <td class="px-3 py-2.5 text-center">
          <div class="editable-cell" data-field="hcd_130">
            <span class="font-mono ${night > 0 ? 'text-purple-600 font-bold' : 'text-slate-400'}">${night}</span>
          </div>
        </td>

        <!-- Editable Meal -->
        <td class="px-3 py-2.5 text-center">
          <div class="editable-cell" data-field="meal_count">
            <span class="font-mono ${meal > 0 ? 'text-emerald-700 font-bold' : 'text-slate-400'}">${meal}</span>
          </div>
        </td>

        <!-- Status -->
        <td class="px-3 py-2.5 text-center">
          <span class="${badgeClass}" title="${escapeHtml((rec.messages || []).join('; '))}">
            ${statusLabel}
          </span>
        </td>

        <!-- Actions -->
        <td class="px-3 py-2.5 text-center space-x-1">
          <button type="button" class="btn-edit-row p-1 text-slate-400 hover:text-indigo-600 transition" title="Sửa chi tiết">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
          </button>
          <button type="button" class="btn-delete-row p-1 text-slate-400 hover:text-rose-600 transition" title="Xóa dòng">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
          </button>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
  attachTableEventListeners();
}

function updateSummaryBadges(summary) {
  const total = summary ? summary.total : state.records.length;
  const valid = summary ? summary.valid : state.records.filter(r => r.status === 'VALID').length;
  const warning = summary ? summary.warning : state.records.filter(r => r.status === 'WARNING').length;
  const error = summary ? summary.error : state.records.filter(r => r.status === 'ERROR').length;

  document.getElementById('count-all').textContent = total;
  document.getElementById('count-valid').textContent = valid;
  document.getElementById('count-warning').textContent = warning;
  document.getElementById('count-error').textContent = error;
}

function attachTableEventListeners() {
  const tbody = document.getElementById('table-body');
  if (!tbody) return;

  // Edit Row button
  tbody.querySelectorAll('.btn-edit-row').forEach(btn => {
    btn.onclick = (e) => {
      const tr = e.target.closest('tr');
      const recId = tr.getAttribute('data-id');
      const rec = state.records.find(r => r.id === recId);
      if (rec) openEditModal(rec);
    };
  });

  // Delete Row button
  tbody.querySelectorAll('.btn-delete-row').forEach(btn => {
    btn.onclick = (e) => {
      const tr = e.target.closest('tr');
      const recId = tr.getAttribute('data-id');
      if (confirm('Bạn có chắc chắn muốn xóa dòng chấm công này?')) {
        state.records = state.records.filter(r => r.id !== recId);
        renderTable();
        updateSummaryBadges();
      }
    };
  });

  // Inline Cell Editing
  tbody.querySelectorAll('.editable-cell').forEach(cell => {
    cell.onclick = function() {
      if (this.querySelector('input, select')) return; // Already editing
      const field = this.getAttribute('data-field');
      const tr = this.closest('tr');
      const recId = tr.getAttribute('data-id');
      const rec = state.records.find(r => r.id === recId);
      if (!rec) return;

      const currentVal = this.textContent.trim();
      const isNumber = ['hcn_100', 'tcn_150', 'hcd_130', 'meal_count'].includes(field);

      const input = document.createElement('input');
      input.type = isNumber ? 'number' : 'text';
      if (isNumber) {
        input.step = '0.5';
        input.min = '0';
      }
      input.value = currentVal;
      input.className = 'w-full text-center px-1 py-0.5 border border-indigo-500 rounded bg-white text-xs outline-none';

      this.innerHTML = '';
      this.appendChild(input);
      input.focus();
      input.select();

      const commit = () => {
        let val = input.value.trim();
        if (isNumber) {
          val = parseFloat(val) || 0;
          if (field === 'hcn_100') rec.hours.hcn_100 = val;
          else if (field === 'tcn_150') rec.hours.tcn_150 = val;
          else if (field === 'hcd_130') rec.hours.hcd_130 = val;
          else if (field === 'meal_count') rec.meal_count = parseInt(val) || 0;
        } else {
          rec[field] = val;
          if (field === 'employee_name') rec.normalized_name = val;
        }
        renderTable();
        updateSummaryBadges();
      };

      input.onblur = commit;
      input.onkeydown = (e) => {
        if (e.key === 'Enter') commit();
        if (e.key === 'Escape') renderTable();
      };
    };
  });
}

// ==============================================================================
// Modal Form Operations
// ==============================================================================

function openEditModal(rec) {
  const modal = document.getElementById('edit-modal');
  const h = rec.hours || {};

  document.getElementById('modal-rec-id').value = rec.id || '';
  document.getElementById('modal-name').value = rec.employee_name || '';
  document.getElementById('modal-date').value = rec.date_str || rec.resolved_date || '';
  document.getElementById('modal-shift').value = (rec.shift_type === 'NIGHT' || rec.shift === 'Ca đêm') ? 'NIGHT' : 'DAY';
  document.getElementById('modal-meal').value = String(rec.meal_count !== undefined ? rec.meal_count : 0);

  document.getElementById('modal-hcn').value = h.hcn_100 !== undefined ? h.hcn_100 : 8.0;
  document.getElementById('modal-tcn').value = h.tcn_150 !== undefined ? h.tcn_150 : 0.0;
  document.getElementById('modal-hcd').value = h.hcd_130 !== undefined ? h.hcd_130 : 0.0;
  document.getElementById('modal-tcd').value = h.tcd_195 !== undefined ? h.tcd_195 : 0.0;
  document.getElementById('modal-cn-day').value = h.sunday_day_200 !== undefined ? h.sunday_day_200 : 0.0;
  document.getElementById('modal-cn-night').value = h.sunday_night_260 !== undefined ? h.sunday_night_260 : 0.0;

  document.getElementById('modal-raw-text').textContent = rec.raw_text || '(Bản ghi nhập thủ công)';

  modal.classList.remove('hidden');
}

function closeEditModal() {
  document.getElementById('edit-modal').classList.add('hidden');
}

function handleModalSubmit(e) {
  e.preventDefault();
  const recId = document.getElementById('modal-rec-id').value;
  let rec = state.records.find(r => r.id === recId);

  if (!rec) {
    // New manual record
    rec = {
      id: 'rec_manual_' + Date.now(),
      hours: {},
      status: 'VALID',
      messages: []
    };
    state.records.push(rec);
  }

  rec.employee_name = document.getElementById('modal-name').value.trim();
  rec.normalized_name = rec.employee_name;
  rec.date_str = document.getElementById('modal-date').value.trim();
  rec.shift_type = document.getElementById('modal-shift').value;
  rec.meal_count = parseInt(document.getElementById('modal-meal').value) || 0;

  rec.hours.hcn_100 = parseFloat(document.getElementById('modal-hcn').value) || 0;
  rec.hours.tcn_150 = parseFloat(document.getElementById('modal-tcn').value) || 0;
  rec.hours.hcd_130 = parseFloat(document.getElementById('modal-hcd').value) || 0;
  rec.hours.tcd_195 = parseFloat(document.getElementById('modal-tcd').value) || 0;
  rec.hours.sunday_day_200 = parseFloat(document.getElementById('modal-cn-day').value) || 0;
  rec.hours.sunday_night_260 = parseFloat(document.getElementById('modal-cn-night').value) || 0;
  rec.status = 'VALID';

  closeEditModal();
  renderTable();
  updateSummaryBadges();
}

function renderExportBanner(data) {
  const banner = document.getElementById('export-result-banner');
  const summary = data.summary || {};

  document.getElementById('res-total-records').textContent = summary.records_processed || state.records.length;
  document.getElementById('res-matched-emps').textContent = summary.employees_matched || summary.employees_updated || 0;
  document.getElementById('res-cells-written').textContent = summary.cells_written || summary.updated_cells || 0;

  // Download button
  const dlBtn = document.getElementById('btn-download-file');
  dlBtn.href = data.download_url;
  dlBtn.setAttribute('download', data.filename);

  // Warnings
  const warnBox = document.getElementById('export-warnings-box');
  const warnList = document.getElementById('export-warnings-list');
  if (summary.errors && summary.errors.length > 0) {
    warnList.innerHTML = summary.errors.map(e => `<li>${escapeHtml(e)}</li>`).join('');
    warnBox.classList.remove('hidden');
  } else {
    warnBox.classList.add('hidden');
  }

  banner.className = 'rounded-xl border border-emerald-200 bg-emerald-50/70 p-5 transition-all shadow-sm';
  banner.classList.remove('hidden');
  banner.scrollIntoView({ behavior: 'smooth' });
}

// ==============================================================================
// Initialization & Event Binding
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
  // Initial template metadata load
  fetchTemplateInfo();

  // Textarea input watcher
  const rawTextarea = document.getElementById('zalo-raw-text');
  if (rawTextarea) {
    rawTextarea.addEventListener('input', updateMessageCounter);
  }

  // Buttons
  const btnSample = document.getElementById('btn-sample');
  if (btnSample) btnSample.addEventListener('click', loadSample);

  const btnClear = document.getElementById('btn-clear');
  if (btnClear) {
    btnClear.addEventListener('click', () => {
      rawTextarea.value = '';
      updateMessageCounter();
    });
  }

  const btnParse = document.getElementById('btn-parse');
  if (btnParse) btnParse.addEventListener('click', handleParse);

  const btnExport = document.getElementById('btn-export');
  if (btnExport) btnExport.addEventListener('click', handleExportExcel);

  // Filter Buttons
  const filterGroup = document.getElementById('filter-group');
  if (filterGroup) {
    filterGroup.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        filterGroup.querySelectorAll('button').forEach(b => {
          b.className = 'px-2.5 py-1 rounded-md hover:text-slate-900';
        });
        btn.className = 'px-2.5 py-1 rounded-md bg-white text-slate-900 shadow-xs font-semibold';
        state.currentFilter = btn.getAttribute('data-filter');
        renderTable();
      });
    });
  }

  // Add Row Button
  const btnAddRow = document.getElementById('btn-add-row');
  if (btnAddRow) {
    btnAddRow.addEventListener('click', () => {
      const newRec = {
        id: 'rec_' + Math.random().toString(36).substring(2, 9),
        employee_name: 'Nhân viên mới',
        date_str: '24/10',
        shift_type: 'DAY',
        hours: {
          hcn_100: 8.0,
          tcn_150: 0.0,
          hcd_130: 0.0,
          tcd_195: 0.0,
          sunday_day_200: 0.0,
          sunday_night_260: 0.0,
          total_hours: 8.0
        },
        meal_count: 0,
        status: 'VALID',
        messages: []
      };
      state.records.push(newRec);
      renderTable();
      updateSummaryBadges();
      openEditModal(newRec);
    });
  }

  // Clear Table Button
  const btnClearTable = document.getElementById('btn-clear-table');
  if (btnClearTable) {
    btnClearTable.addEventListener('click', () => {
      if (confirm('Bạn có chắc chắn muốn xóa toàn bộ bảng dữ liệu xem trước?')) {
        state.records = [];
        renderTable();
        updateSummaryBadges();
      }
    });
  }

  // Template Option Radios
  const radioDefault = document.getElementById('radio-default-tpl');
  const radioCustom = document.getElementById('radio-custom-tpl');
  const uploadWrapper = document.getElementById('upload-box-wrapper');
  const fileInput = document.getElementById('template-upload');

  if (radioDefault && radioCustom) {
    radioDefault.addEventListener('change', () => {
      state.useCustomTemplate = false;
      uploadWrapper.classList.add('hidden');
      fetchTemplateInfo();
    });
    radioCustom.addEventListener('change', () => {
      state.useCustomTemplate = true;
      uploadWrapper.classList.remove('hidden');
    });
  }

  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleTemplateUpload(e.target.files[0]);
      }
    });
  }

  // Modal Handlers
  const modalClose = document.getElementById('modal-close');
  const modalCancel = document.getElementById('modal-cancel-btn');
  const modalForm = document.getElementById('modal-form');

  if (modalClose) modalClose.addEventListener('click', closeEditModal);
  if (modalCancel) modalCancel.addEventListener('click', closeEditModal);
  if (modalForm) modalForm.addEventListener('submit', handleModalSubmit);
});
