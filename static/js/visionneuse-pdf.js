function openPdf(url, title) {
  document.getElementById('pdf-title').textContent = title || 'Document';
  document.getElementById('pdf-frame').src = url;
  document.getElementById('pdf-viewer').hidden = false;
}
function closePdf() {
  document.getElementById('pdf-frame').src = 'about:blank';   // libère le PDF
  document.getElementById('pdf-viewer').hidden = true;
}
document.getElementById('pdf-viewer').addEventListener('click', e => { if (e.target.id === 'pdf-viewer') closePdf(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !document.getElementById('pdf-viewer').hidden) closePdf(); });
