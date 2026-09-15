document.addEventListener('DOMContentLoaded', () => {
    const endpointInput = document.getElementById('api-endpoint');
    const form = document.getElementById('query-form');
    const repoInput = document.getElementById('repo-input');
    const questionInput = document.getElementById('question-input');
    const submitBtn = document.getElementById('submit-btn');
    const loadingSection = document.getElementById('loading');
    const resultsSection = document.getElementById('results-section');
    const statusMessage = document.getElementById('status-message');
    const answerContent = document.getElementById('answer-content');
    const sourcesList = document.getElementById('sources-list');

    // Load saved endpoint
    const savedEndpoint = localStorage.getItem('repomind_endpoint');
    if (savedEndpoint) {
        endpointInput.value = savedEndpoint;
    }

    // Save endpoint on change
    endpointInput.addEventListener('change', (e) => {
        localStorage.setItem('repomind_endpoint', e.target.value.trim());
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const endpoint = endpointInput.value.trim();
        const repo = repoInput.value.trim();
        const question = questionInput.value.trim();

        if (!endpoint || !repo || !question) {
            showError("Please fill in all fields.");
            return;
        }

        if (!endpoint.startsWith('https://')) {
            showError("API Endpoint must be an HTTPS URL.");
            return;
        }

        // Reset UI
        resultsSection.classList.add('hidden');
        statusMessage.className = 'status-message hidden';
        answerContent.innerHTML = '';
        sourcesList.innerHTML = '';
        
        // Show loading state
        submitBtn.disabled = true;
        loadingSection.classList.remove('hidden');

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    repo: repo,
                    question: question
                })
            });

            if (!response.ok) {
                let errorMsg = `HTTP Error ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) errorMsg += `: ${errorData.error}`;
                } catch (e) {
                    // Ignore non-json response
                }
                throw new Error(errorMsg);
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            showError(error.message || "Failed to connect to the API. Check the endpoint URL and CORS settings.");
        } finally {
            submitBtn.disabled = false;
            loadingSection.classList.add('hidden');
        }
    });

    function showError(message) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message error';
        resultsSection.classList.remove('hidden');
    }

    function formatMarkdown(text) {
        if (!text) return '';
        
        // Simple markdown parsing
        let formatted = text
            // Code blocks
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Bold
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            // Newlines to br
            .replace(/\n/g, '<br>');
            
        return formatted;
    }

    function displayResults(data) {
        if (!data.answer) {
            showError("No answer received from API.");
            return;
        }

        // Display Answer
        answerContent.innerHTML = formatMarkdown(data.answer);

        // Display Sources
        if (data.sources && data.sources.length > 0) {
            const sourcesHTML = data.sources.map(source => `
                <div class="source-card">
                    <div class="source-header">
                        <span class="file-path">${escapeHtml(source.file_path)}</span>
                        ${source.relevance_score ? `<span class="score">Score: ${(source.relevance_score * 100).toFixed(1)}%</span>` : ''}
                    </div>
                    <div class="source-details">
                        Lines ${source.start_line}-${source.end_line}
                        ${source.symbol ? `&bull; <span class="source-symbol">${escapeHtml(source.symbol)}</span> (${escapeHtml(source.symbol_type)})` : ''}
                    </div>
                </div>
            `).join('');
            
            sourcesList.innerHTML = sourcesHTML;
            sourcesList.parentElement.classList.remove('hidden');
        } else {
            sourcesList.innerHTML = '<p class="source-details">No specific code sources referenced.</p>';
        }

        // Show results section
        statusMessage.className = 'status-message hidden';
        resultsSection.classList.remove('hidden');
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return (unsafe+'')
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }
});
