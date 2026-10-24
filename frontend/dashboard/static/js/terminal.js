/**
 * Terminal & Log Streamer with ANSI & Tag Highlighting
 */

class TerminalViewer {
  constructor(elementId) {
    this.container = document.getElementById(elementId);
    this.autoScroll = true;
    this.lines = [];
  }

  escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  colorize(text) {
    let escaped = this.escapeHtml(text);

    // Common game tester tokens
    escaped = escaped.replace(/(\[OK\]|\[TARGET REACHED\]|\[ALL WAYPOINTS COMPLETED\]|SUCCESS)/g, '<span class="term-ok">$1</span>');
    escaped = escaped.replace(/(\[ERROR\]|\[FAIL\]|\[\!\]|EXCEPTION)/g, '<span class="term-err">$1</span>');
    escaped = escaped.replace(/(\[WARNING\]|\[WARN\]|\[NOTE\]|\[AUTO-RETRY\])/g, '<span class="term-warn">$1</span>');
    escaped = escaped.replace(/(\[INFO\]|\[DASHBOARD\]|\[Loop\]|\[CoordinateLoader\])/g, '<span class="term-info">$1</span>');
    escaped = escaped.replace(/(\[NAVIGATE\]|\[WAYPOINT.*?\]|\[Step.*?\])/g, '<span class="term-nav">$1</span>');
    escaped = escaped.replace(/(\[BUGTRIGGER.*?\])/g, '<span class="term-bug">$1</span>');

    // Coordinate pairs highlight
    escaped = escaped.replace(/\((\d+\.?\d*),\s*(-?\d+\.?\d*)\)/g, '<span style="color:#38bdf8;font-weight:600;">($1, $2)</span>');

    return escaped;
  }

  append(line) {
    this.lines.push(line);
    const lineEl = document.createElement("div");
    lineEl.className = "term-line";
    lineEl.innerHTML = this.colorize(line);
    this.container.appendChild(lineEl);

    // Cap DOM nodes to 2500 for high performance
    if (this.container.children.length > 2500) {
      this.container.removeChild(this.container.firstChild);
    }

    if (this.autoScroll) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  }

  clear() {
    this.container.innerHTML = "";
    this.lines = [];
  }

  copy() {
    navigator.clipboard.writeText(this.lines.join("\n"));
  }

  download() {
    const blob = new Blob([this.lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `run_logs_${new Date().toISOString().replace(/[:.]/g, "-")}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

