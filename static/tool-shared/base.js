/* SG AI工具共享JS v2.0 */
var SG = SG || {};

// ── HTML转义（防XSS）──
SG.escHtml = function(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
};

// ── 快捷DOM ──
SG.$ = function(id) { return document.getElementById(id); };

// ── Toast通知 ──
SG.showToast = function(msg, type, duration) {
  var t = document.createElement('div');
  t.className = 'toast';
  t.style.background = type === 'error' ? '#e74c3c' : type === 'warn' ? '#f39c12' : '#27ae60';
  t.textContent = msg;
  document.body.appendChild(t);
  duration = duration || 2500;
  setTimeout(function() {
    t.style.opacity = '0';
    setTimeout(function() { t.remove(); }, 300);
  }, duration);
};

// ── 工具基类 ──
SG.ToolBase = function(config) {
  this.apiBase = config.apiBase;       // '/api/v1/seo-tool'
  this.taskId = null;
  this.generating = false;
  this.startTime = 0;
  this.pollTimer = null;
  this.stepTimer = null;
  this.stepTexts = config.stepTexts || ['提交任务...', 'AI思考中...', '整理结果中...'];
  this.timeout = config.timeout || 120000;
  this.pollInterval = config.pollInterval || 3000;
};

SG.ToolBase.prototype.getClientIP = function() { return 'unknown'; };

// ── 配额同步 ──
SG.ToolBase.prototype.syncQuota = function() {
  var self = this;
  fetch(this.apiBase + '/quota').then(function(r) {
    if (!r.ok) return;
    return r.json();
  }).then(function(d) {
    if (!d) return;
    var el = SG.$('quotaText');
    if (el) {
      el.textContent = '剩余 ' + d.remaining + ' / ' + d.limit + ' 次';
      el.className = 'rem' + (d.remaining === 0 ? ' zero' : d.remaining === 1 ? ' low' : '');
    }
  }).catch(function() {
    var el = SG.$('quotaText');
    if (el) el.textContent = '免费3次/天';
  });
};

// ── 进度动画 ──
SG.ToolBase.prototype.startSteps = function() {
  var self = this;
  var idx = 0;
  var progressArea = SG.$('progressArea');
  var stepsEl = SG.$('steps');
  if (progressArea) progressArea.classList.remove('hidden');
  if (stepsEl) stepsEl.innerHTML = '<div class="step"><div class="dot">1</div><div class="txt">任务已提交</div></div>';
  
  this.stepTimer = setInterval(function() {
    idx++;
    if (idx >= self.stepTexts.length) idx = self.stepTexts.length - 1;
    var html = '';
    for (var i = 0; i <= idx; i++) {
      html += '<div class="step"><div class="dot' + (i < idx ? ' done' : '') + '">' + (i + 1) + '</div><div class="txt">' + self.stepTexts[i] + '</div></div>';
    }
    if (stepsEl) stepsEl.innerHTML = html;
  }, 5000);
};

SG.ToolBase.prototype.stopSteps = function() {
  if (this.stepTimer) { clearInterval(this.stepTimer); this.stepTimer = null; }
};

// ── 轮询 ──
SG.ToolBase.prototype.startPolling = function() {
  var self = this;
  this.pollTimer = setInterval(function() {
    if (Date.now() - self.startTime > self.timeout) {
      clearInterval(self.pollTimer);
      self.generating = false;
      self.stopSteps();
      self.resetButton();
      self.showError('生成超时，请稍后重试');
      return;
    }
    fetch(self.apiBase + '/task/' + encodeURIComponent(self.taskId))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status === 'done') {
          clearInterval(self.pollTimer);
          self.generating = false;
          self.stopSteps();
          self.resetButton();
          if (typeof self.onResult === 'function') self.onResult(data.result);
          self.syncQuota();
        } else if (data.status === 'error') {
          clearInterval(self.pollTimer);
          self.generating = false;
          self.stopSteps();
          self.resetButton();
          self.showError(data.error || '生成失败');
        } else if (data.progress) {
          // 更新进度文字
          var stepsEl = SG.$('steps');
          if (stepsEl && stepsEl.lastElementChild) {
            var txtEl = stepsEl.lastElementChild.querySelector('.txt');
            if (txtEl) txtEl.textContent = data.progress;
          }
        }
      })
      .catch(function(){});
  }, this.pollInterval);
};

// ── 错误展示 ──
SG.ToolBase.prototype.showError = function(msg) {
  var errorArea = SG.$('errorArea');
  var errorMsg = SG.$('errorMsg');
  var resultArea = SG.$('resultArea');
  var progressArea = SG.$('progressArea');
  if (errorArea) errorArea.classList.remove('hidden');
  if (errorMsg) errorMsg.textContent = msg;
  if (resultArea) resultArea.classList.add('hidden');
  if (progressArea) progressArea.classList.add('hidden');
};

// ── 提交任务 ──
SG.ToolBase.prototype.submit = function(endpoint, body, btnLabel) {
  var self = this;
  if (this.generating) return;
  
  this.generating = true;
  this.startTime = Date.now();
  
  var btn = SG.$('genBtn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>' + (btnLabel || '生成中...'); }
  
  var errorArea = SG.$('errorArea');
  var resultArea = SG.$('resultArea');
  if (errorArea) errorArea.classList.add('hidden');
  if (resultArea) resultArea.classList.add('hidden');
  
  this.startSteps();
  
  fetch(this.apiBase + endpoint, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  }).then(function(r) {
    if (!r.ok) return r.json().then(function(d) { throw new Error(d.detail || '请求失败'); });
    return r.json();
  }).then(function(d) {
    if (d.success && d.task_id) { self.taskId = d.task_id; self.startPolling(); }
    else { throw new Error(d.message || d.error || '提交失败'); }
  }).catch(function(err) {
    self.generating = false;
    self.stopSteps();
    self.resetButton();
    self.showError(err.message || '网络错误');
  });
};

// ── 重置按钮 ──
SG.ToolBase.prototype.resetButton = function() {
  var btn = SG.$('genBtn');
  if (btn) {
    btn.disabled = false;
    // 恢复按钮原文（各工具不同）
    if (typeof this.getButtonLabel === 'function') {
      btn.innerHTML = this.getButtonLabel();
    }
  }
};

// ── 复制结果 ──
SG.ToolBase.prototype.copyResult = function() {
  var el = SG.$('resultContent');
  if (!el) return;
  var text = el.innerText;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(function() { SG.showToast('已复制到剪贴板'); });
  }
};

// ── 导出JSON ──
SG.ToolBase.prototype.exportJSON = function() {
  if (!this._lastResult) return;
  var blob = new Blob([JSON.stringify(this._lastResult, null, 2)], {type: 'application/json'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'result_' + new Date().toISOString().slice(0,10) + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
  SG.showToast('JSON已导出');
};

// ── Style Chips交互 ──
SG.initChips = function(containerId) {
  var container = SG.$(containerId);
  if (!container) return;
  container.addEventListener('click', function(e) {
    var chip = e.target.closest('.chip');
    if (!chip) return;
    container.querySelectorAll('.chip').forEach(function(c) { c.classList.remove('active'); });
    chip.classList.add('active');
  });
};

// ── 获取当前激活的chip值 ──
SG.getActiveChip = function(containerId) {
  var container = SG.$(containerId);
  if (!container) return '';
  var active = container.querySelector('.chip.active');
  return active ? active.getAttribute('data-val') : '';
};
