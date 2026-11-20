(() => {
  const $ = (selector) => document.querySelector(selector);
  const input = $('#file'), dropzone = $('#dropzone');
  let selected = null, previewUrl = null;
  const showError = (message = '') => { $('#error').textContent = message; $('#error').hidden = !message; };
  fetch('/api/health').then((r) => r.json()).then((data) => {
    const ready = data.model === 'available';
    $('#health-dot').classList.toggle('ready', ready);
    $('#health-label').textContent = ready ? 'MODEL AVAILABLE' : 'MODEL MISSING';
  }).catch(() => { $('#health-label').textContent = 'BACKEND UNAVAILABLE'; });

  function setFile(file) {
    showError(); if (!file) return;
    if (!['image/jpeg', 'image/png'].includes(file.type)) return showError('Choose a JPG, JPEG, or PNG image.');
    if (file.size > 4 * 1024 * 1024) return showError('This image is larger than 4 MB. Choose a smaller image.');
    selected = file;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    const img = $('#preview'); img.src = previewUrl;
    img.onload = () => { $('#dimensions').textContent = `${img.naturalWidth} × ${img.naturalHeight} px · ${(file.size / 1048576).toFixed(2)} MB`; };
    $('#filename').textContent = file.name; $('#selected').hidden = false; dropzone.hidden = true; $('#analyze').disabled = false; $('#results').hidden = true;
  }
  input.addEventListener('change', () => setFile(input.files[0]));
  for (const eventName of ['dragenter', 'dragover']) dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.add('drag'); });
  for (const eventName of ['dragleave', 'drop']) dropzone.addEventListener(eventName, (event) => { event.preventDefault(); dropzone.classList.remove('drag'); });
  dropzone.addEventListener('drop', (event) => setFile(event.dataTransfer.files[0]));
  $('#remove').addEventListener('click', () => { selected = null; input.value = ''; $('#selected').hidden = true; dropzone.hidden = false; $('#analyze').disabled = true; if (previewUrl) URL.revokeObjectURL(previewUrl); });
  $('#analyze').addEventListener('click', async () => {
    if (!selected) return;
    const button = $('#analyze'); button.disabled = true; $('#progress').hidden = false; showError(); $('#results').hidden = true;
    const body = new FormData(); body.append('image', selected);
    try {
      const response = await fetch('/api/analyze', { method: 'POST', body });
      const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Image analysis failed.');
      $('#result-title').textContent = data.detected ? 'Potential crack detected' : 'No crack detected';
      $('#badge').textContent = data.detected ? 'REVIEW RECOMMENDED' : 'NO DETECTION'; $('#badge').classList.toggle('detected', data.detected);
      $('#count').textContent = data.count; $('#confidence').textContent = data.confidence == null ? '—' : `${(data.confidence * 100).toFixed(1)}%`;
      $('#time').textContent = `${data.processing_ms} ms`; $('#size').textContent = `${data.width} × ${data.height}`;
      $('#original-output').src = previewUrl; $('#annotated').src = data.output_image; $('#download-original').href = previewUrl; $('#download-original').download = selected.name; $('#download-result').href = data.output_image;
      $('#results').hidden = false; $('#results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { showError(error.message || 'Unable to reach the analyzer.'); }
    finally { $('#progress').hidden = true; button.disabled = !selected; }
  });
  $('#clear').addEventListener('click', () => { $('#results').hidden = true; });
})();
