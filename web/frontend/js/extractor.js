document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('ext-submit-url');
    const urlInput = document.getElementById('ext-url-input');
    const dropZone = document.getElementById('ext-drop-zone');
    const fileInput = document.getElementById('ext-file-input');
    
    const inputZone = document.querySelector('#workspace-extractor .input-zone');
    const statusZone = document.getElementById('ext-status');
    const resultsZone = document.getElementById('ext-results');
    
    const jobIdSpan = document.getElementById('ext-job-id');
    const statusText = statusZone.querySelector('.status-text');

    function showStatus(jobId) {
        inputZone.classList.add('hidden');
        resultsZone.classList.add('hidden');
        statusZone.classList.remove('hidden');
        jobIdSpan.textContent = jobId;
        statusText.textContent = "Extracting audio...";
        
        // Listen to SSE
        App.subscribeToJob(jobId, 
            (data) => {
                // on update
            },
            (result) => {
                // on complete
                showResults(result);
            },
            (err) => {
                // on error
                statusText.textContent = `Error: ${err}`;
                document.querySelector('#workspace-extractor .loader').classList.add('hidden');
            }
        );
    }

    function showResults(result) {
        statusZone.classList.add('hidden');
        resultsZone.classList.remove('hidden');
        
        App.embedVideo('ext-video-container', result.video_embed_url);
        
        document.getElementById('ext-filename').textContent = result.filename;
        document.getElementById('ext-audio').src = result.audio_url;
        document.getElementById('ext-download-btn').href = result.audio_url;
        document.getElementById('ext-download-btn').download = result.filename;
    }

    submitBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) return;
        
        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Starting...';
            
            const res = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            
            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);
            
        } catch (e) {
            alert('Failed to start job');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Extract';
        }
    });

    // Drag and Drop
    dropZone.addEventListener('click', () => fileInput.click());
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;
        if (files.length) uploadFile(files[0]);
    });

    fileInput.addEventListener('change', function() {
        if (this.files.length) uploadFile(this.files[0]);
    });

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const p = dropZone.querySelector('p');
            const originalText = p.innerHTML;
            p.textContent = 'Uploading...';
            
            const res = await fetch('/api/extract/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await res.json();
            if (data.job_id) showStatus(data.job_id);
            
            p.innerHTML = originalText;
        } catch (e) {
            alert('Failed to upload file');
        }
    }
});
