// Paste into the browser console (Cmd+Option+J / Ctrl+Shift+J) on a
// Motley Fool earnings call transcript page. It replaces the page with a
// single text box holding only the call - no ads, no editorial summary -
// already selected so you can copy it straight into Night Desk.
(() => {
  const t = (document.querySelector('.article-body') || document.body).innerText;
  const start = t.indexOf('Full Conference Call Transcript');
  if (start < 0) { alert('Could not find "Full Conference Call Transcript" on this page.'); return; }
  let b = t.slice(start);
  const end = b.search(/\n[^\n]*(Investor Blunders|Fisher Investments|SPONSORED CONTENT|Premium Investing Services)/);
  if (end > 0) b = b.slice(0, end);
  b = b.replace(/^Full Conference Call Transcript\s*/, '').trim();
  b = document.title.replace(/\s*\|.*$/, '').toUpperCase() + '\n\n' + b;
  document.documentElement.innerHTML =
    '<body style="margin:0;background:#06080b"><textarea id="tx" style="width:100vw;height:100vh;' +
    'background:#0b0f14;color:#d7dee7;border:0;padding:16px;font:12px monospace"></textarea></body>';
  const tx = document.getElementById('tx');
  tx.value = b; tx.focus(); tx.select();
})();
