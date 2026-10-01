function setupResumeForm() {
  const resumeForm = document.querySelector('#resume-form');
  if (!resumeForm || resumeForm.dataset.bound === 'true') return;
  resumeForm.dataset.bound = 'true';

  const resumeFile = document.querySelector('#resume-file');
  const uploadZone = document.querySelector('#upload-zone');
  const uploadFilename = document.querySelector('#upload-filename');

  function showFile(file) {
    if (!file) return;
    const allowed = /\.(pdf|docx|txt)$/i.test(file.name);
    const underLimit = file.size <= 5 * 1024 * 1024;
    if (!allowed || !underLimit) {
      uploadFilename.textContent = !allowed ? 'Choose a PDF, DOCX, or TXT file.' : 'This file is over 5 MB.';
      uploadFilename.classList.add('file-error');
      resumeFile.value = '';
      return;
    }
    uploadFilename.classList.remove('file-error');
    uploadFilename.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB`;
    uploadZone.classList.add('has-file');
  }

  resumeFile?.addEventListener('change', () => showFile(resumeFile.files[0]));
  ['dragenter', 'dragover'].forEach((eventName) => uploadZone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.add('is-dragging');
  }));
  ['dragleave', 'drop'].forEach((eventName) => uploadZone?.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadZone.classList.remove('is-dragging');
  }));
  uploadZone?.addEventListener('drop', (event) => {
    const [file] = event.dataTransfer.files;
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    resumeFile.files = transfer.files;
    showFile(file);
  });

  resumeForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!resumeFile.files.length) return;

    const button = document.querySelector('#analyze-button');
    const progress = document.querySelector('#analysis-progress');
    const stage = document.querySelector('#analysis-stage');
    const substage = document.querySelector('#analysis-substage');
    button.disabled = true;
    button.hidden = true;
    progress.hidden = false;

    const stages = [
      ['Extracting document text', 'Reading the visible content in your file.'],
      ['Matching your target role', 'Comparing skills with the selected role.'],
      ['Checking structure and keywords', 'Building a practical compatibility view.'],
      ['Preparing recommendations', 'Keeping suggestions grounded in your resume.'],
    ];
    const startedAt = Date.now();
    let stageIndex = 0;
    let lastWaitNotice = 0;
    const stageTimer = window.setInterval(() => {
      const elapsedSeconds = Math.floor((Date.now() - startedAt) / 1000);
      if (stageIndex < stages.length) {
        stage.textContent = stages[stageIndex][0];
        substage.textContent = stages[stageIndex][1];
        stageIndex += 1;
      } else {
        if (stage.textContent !== 'Still analyzing your resume') {
          stage.textContent = 'Still analyzing your resume';
        }
        if (elapsedSeconds - lastWaitNotice >= 5) {
          substage.textContent = `Still working · ${elapsedSeconds}s elapsed. Your report will appear when analysis finishes.`;
          lastWaitNotice = elapsedSeconds;
        }
      }
    }, 1400);

    try {
      const response = await fetch(resumeForm.action, {
        method: 'POST',
        body: new FormData(resumeForm),
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const html = await response.text();
      const parsedPage = new DOMParser().parseFromString(html, 'text/html');
      const nextMain = parsedPage.querySelector('#main');
      if (!nextMain) throw new Error('The server returned an unreadable page.');

      document.title = parsedPage.title;
      document.querySelector('#main').replaceChildren(...nextMain.childNodes);
      history.pushState({}, '', response.ok ? '/resume/report' : '/resume');
      setupResumeForm();
    } catch {
      progress.hidden = true;
      button.hidden = false;
      button.disabled = false;
      let error = document.querySelector('#analysis-error');
      if (!error) {
        error = document.createElement('p');
        error.id = 'analysis-error';
        error.className = 'field-error';
        error.setAttribute('role', 'alert');
        resumeForm.insertBefore(error, progress);
      }
      error.textContent = 'We couldn’t reach the analysis service. Your file is still on this page; try again.';
    } finally {
      window.clearInterval(stageTimer);
    }
  });
}

setupResumeForm();
window.addEventListener('popstate', () => window.location.reload());