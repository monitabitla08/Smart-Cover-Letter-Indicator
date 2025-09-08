document.getElementById('run-btn').addEventListener('click', async function() {
    const resume = document.getElementById('resume').value;
    const jobDescription = document.getElementById('job_description').value;
    const gapsDiv = document.getElementById('gaps');
    const coverDiv = document.getElementById('cover_letter');
    gapsDiv.textContent = 'Running...';
    coverDiv.textContent = '';
    try {
        const response = await fetch('/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ resume, job_description: jobDescription })
        });
        if (!response.ok) {
            const err = await response.json();
            gapsDiv.textContent = err.error || 'Error occurred.';
            coverDiv.textContent = '';
            return;
        }
        const data = await response.json();
        gapsDiv.innerHTML = data.gaps ? marked.parse(data.gaps) : 'No gap/match report.';
        coverDiv.innerHTML = data.cover_letter ? marked.parse(data.cover_letter) : 'No cover letter.';
    } catch (e) {
        gapsDiv.textContent = 'Error: ' + e.message;
        coverDiv.textContent = '';
    }
});

// Load Marked.js for markdown rendering
(function() {
    var script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    script.onload = function() {
        // Marked loaded
    };
    document.head.appendChild(script);
})();
