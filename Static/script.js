/**
 * Adaptive Lecture Summarizer - Frontend JavaScript
 * ==================================================
 * 
 * Project: Adaptive learning platform
 * File: static/script.js
 * Purpose: Handle all client-side functionality
 * 
 * Features:
 * 1. Knowledge Level Slider Management
 *    - 5 discrete levels (0-4): Complete Beginner → Expert
 *    - Real-time label updates
 *    - Instant summary switching after generation
 * 
 * 2. Streaming Summary Reception
 *    - Server-Sent Events (SSE) for real-time streaming
 *    - Character-by-character typewriter effect
 *    - Smooth animations and transitions
 *    - Handles 5 parallel summary levels
 * 
 * 3. Quiz System
 *    - Generate natural language questions
 *    - Submit and evaluate answers
 *    - Display color-coded feedback
 *    - Manage quiz state
 * 
 * 4. Markdown Parsing
 *    - Convert markdown to HTML on the fly
 *    - Handle headers, lists, bold, code
 *    - Section-based organization
 * 
 * API Endpoints Used:
 * - POST /process_stream: Stream summaries via SSE
 * - POST /generate_quiz: Get quiz questions
 * - POST /evaluate_answer: Evaluate user answers
 * 
 * Global State:
 * - allSummaries: Object storing all 5 summary levels
 * - quizQuestions: Array of current quiz questions
 * - currentTranscript: Stored for quiz generation
 * 
 * Author: Hackathon Team
 * Date: November 2025
 */

// Initialize slider
const slider = document.getElementById('knowledgeSlider');
const valueDisplay = document.getElementById('knowledgeValue');
const labelDisplay = document.getElementById('knowledgeLabel');
const badgeTop = document.getElementById('knowledgeBadgeTop');

// Store all 5 summaries
let allSummaries = null;

// Map slider value to level (0-4)
function getLevel(sliderValue) {
    const value = sliderValue / 100;
    if (value < 0.2) return 0;
    if (value < 0.4) return 1;
    if (value < 0.6) return 2;
    if (value < 0.8) return 3;
    return 4;
}

// Get level label
function getLevelLabel(level) {
    const labels = [
        'Complete Beginner',
        'Beginner', 
        'Intermediate',
        'Advanced',
        'Expert'
    ];
    return labels[level];
}

slider.addEventListener('input', function() {
    const value = (this.value / 100).toFixed(1);
    const level = getLevel(this.value);
    
    valueDisplay.textContent = value;
    labelDisplay.textContent = getLevelLabel(level);
    badgeTop.textContent = getLevelLabel(level);
    
    // If we already have summaries, update display instantly
    if (allSummaries) {
        displaySummary(level);
    }
});

function displaySummary(level) {
    if (!allSummaries) {
        console.error('No summaries available');
        return;
    }
    
    const summary = allSummaries[level.toString()];
    if (!summary) {
        console.error('Summary not found for level:', level);
        console.error('Available levels:', Object.keys(allSummaries));
        return;
    }
    
    // Update knowledge badge
    document.getElementById('knowledgeBadge').textContent = getLevelLabel(level) + ' Level';
    
    // Parse and display result with animations
    const htmlContent = parseMarkdownToHTML(summary);
    document.getElementById('resultContent').innerHTML = htmlContent;
    document.getElementById('result').style.display = 'block';
}

// Load example transcript
function loadExample() {
    const exampleText = "Natural Language Processing (NLP) is a field of artificial intelligence focused on enabling computers to understand, analyze, and generate human language. It includes techniques such as text analysis, entity recognition, sentiment analysis, speech recognition, and machine translation—all of which help systems extract meaning from written or spoken inputs. NLP also supports conversational AI, where bots interact with users across channels like web chat, email, and voice interfaces. Azure provides various NLP-related tools and services, including text analytics, translation, conversational language understanding, and question answering, helping developers build intelligent language-driven applications and knowledge bases.\n\nTo analyze language effectively, NLP relies on core processes such as tokenization, text normalization, removal of stop words, frequency analysis, and the use of n-grams to capture multi-word expressions. These techniques support downstream tasks like sentiment classification using machine learning algorithms and TF-IDF to identify important terms within documents. More advanced approaches involve semantic language models and word embeddings—such as Word2Vec, which learns vector representations of words based on their context within sentences. Methods like CBOW and Skip-Gram allow models to capture semantic relationships, enabling computers to understand how words relate to one another in meaning-rich ways.";
    document.getElementById('transcriptInput').value = exampleText;
}

// Parse markdown to HTML
function parseMarkdownToHTML(markdown) {
    if (!markdown || typeof markdown !== 'string') {
        console.error('Invalid markdown input:', markdown);
        return '<p>Error: Invalid summary format</p>';
    }
    
    const sections = [];
    const lines = markdown.split('\n');
    let currentSection = null;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.startsWith('## ')) {
            if (currentSection) {
                sections.push(currentSection);
            }
            currentSection = {
                title: line.replace('## ', '').trim(),
                content: []
            };
        } else if (currentSection) {
            currentSection.content.push(line);
        }
    }
    
    if (currentSection) {
        sections.push(currentSection);
    }
    
    // Convert each section to HTML
    const htmlParts = [];
    for (let j = 0; j < sections.length; j++) {
        const section = sections[j];
        let html = '<div class="summary-section"><h2>' + getEmojiForSection(section.title) + ' ' + section.title + '</h2>';
        
        let content = section.content.join('\n');
        
        // Convert markdown to HTML
        content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.+?)\*/g, '<em>$1</em>');
        content = content.replace(/`(.+?)`/g, '<code>$1</code>');
        content = content.replace(/^- (.+)$/gm, '<li>$1</li>');
        content = content.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
        content = content.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        
        // Handle paragraphs
        const paragraphs = content.split('\n\n');
        const contentParts = [];
        for (let k = 0; k < paragraphs.length; k++) {
            const p = paragraphs[k].trim();
            if (!p) continue;
            if (p.startsWith('<ul>') || p.startsWith('<h3>') || p.startsWith('<li>')) {
                contentParts.push(p);
            } else {
                contentParts.push('<p>' + p + '</p>');
            }
        }
        content = contentParts.join('');
        
        html += content + '</div>';
        htmlParts.push(html);
    }
    
    return htmlParts.join('');
}

// Get emoji for section title
function getEmojiForSection(title) {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('key concept')) return '📚';
    if (lowerTitle.includes('takeaway')) return '💡';
    if (lowerTitle.includes('detail')) return '🔍';
    if (lowerTitle.includes('focus') || lowerTitle.includes('suggest')) return '🎯';
    return '📌';
}

// Store quiz data
let quizQuestions = [];
let currentTranscript = '';
let selectedLanguage = 'en';

// File Upload State
let currentInputMode = 'text';
let uploadedFileText = null;
let appConfig = null;

// Memory System State
let memoryMode = false;
let memorySources = [];
let sessionId = null;  // Store session ID in JavaScript

// Load configuration on page load
async function loadConfig() {
    try {
        const response = await fetch('/config');
        appConfig = await response.json();

        // Update UI with config values
        document.getElementById('maxPdfSize').textContent = `${appConfig.max_pdf_size_mb}MB`;
        document.getElementById('maxAudioSize').textContent = `${appConfig.max_audio_size_mb}MB`;

        console.log('App config loaded:', appConfig);
    } catch (err) {
        console.error('Failed to load config:', err);
    }
}

// Call on page load
window.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    initMemorySystem();

    // Add event listener to text input to update button state
    const transcriptInput = document.getElementById('transcriptInput');
    if (transcriptInput) {
        transcriptInput.addEventListener('input', updateMemoryUI);
    }
});

// ============================================================================
// MEMORY SYSTEM FUNCTIONS
// ============================================================================

// Initialize memory system on page load
async function initMemorySystem() {
    try {
        const response = await fetch('/memory/get', {
            credentials: 'include'
        });
        const data = await response.json();

        if (data.success && data.sources.length > 0) {
            memorySources = data.sources;
            memoryMode = true;
            displayMemorySources();
            updateMemoryUI();
        }
    } catch (err) {
        console.error('Failed to load memory:', err);
    }
}

// Handle generate summary button click
function handleGenerateSummary() {
    // Determine if we should use memory mode
    const useMemory = memorySources.length > 0;

    if (useMemory) {
        processSummary(true);
    } else {
        processSummary(false);
    }
}

// Add content to memory
async function addToMemory() {
    const transcriptInput = document.getElementById('transcriptInput');
    const text = transcriptInput.value.trim();

    if (!text || text.length < 10) {
        showError('Please enter at least 10 characters to add to memory');
        return;
    }

    try {
        // Determine source type and filename
        let sourceType = 'text';
        let filename = 'Text Input';

        if (currentInputMode === 'pdf' && uploadedFileText) {
            sourceType = 'pdf';
            filename = document.getElementById('pdfFilename')?.textContent || 'PDF Document';
        } else if (currentInputMode === 'audio' && uploadedFileText) {
            sourceType = 'audio';
            filename = document.getElementById('audioFilename')?.textContent || 'Audio Transcription';
        }

        const response = await fetch('/memory/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                text: text,
                source_type: sourceType,
                filename: filename
            })
        });

        const data = await response.json();

        if (data.success) {
            memorySources.push(data.source_added);
            displayMemorySources();
            updateMemoryUI();

            // Clear input for next source
            transcriptInput.value = '';
            clearFileUpload(currentInputMode);

            showSuccess(`Added to memory! Total sources: ${data.source_count}`);
        } else {
            showError('Failed to add to memory');
        }
    } catch (err) {
        console.error('Add to memory error:', err);
        showError('Failed to add to memory: ' + err.message);
    }
}

// Display memory sources in UI
function displayMemorySources() {
    const sourcesList = document.getElementById('memorySourcesList');

    if (!sourcesList) return;

    if (memorySources.length === 0) {
        sourcesList.innerHTML = '<p class="empty-memory">No sources added yet. Add text, PDF, or audio to build your lecture.</p>';
        return;
    }

    const sourceCards = memorySources.map((source, index) => {
        const icon = {
            'text': '✍️',
            'pdf': '📄',
            'audio': '🎤'
        }[source.type] || '📄';

        const timestamp = new Date(source.timestamp).toLocaleString();

        return `
            <div class="source-card">
                <div class="source-header">
                    <span class="source-icon">${icon}</span>
                    <span class="source-filename">${source.filename}</span>
                    <button class="remove-source-btn" onclick="removeSource(${index})" title="Remove this source">✕</button>
                </div>
                <div class="source-preview">${source.preview}</div>
                <div class="source-meta">Added: ${timestamp}</div>
            </div>
        `;
    }).join('');

    sourcesList.innerHTML = sourceCards;
}

// Remove a source from memory
async function removeSource(index) {
    try {
        const response = await fetch(`/memory/remove/${index}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            memorySources.splice(index, 1);
            displayMemorySources();
            updateMemoryUI();
            showSuccess('Source removed');
        } else {
            showError('Failed to remove source');
        }
    } catch (err) {
        console.error('Remove source error:', err);
        showError('Failed to remove source');
    }
}

// Save memory to file
async function saveMemory() {
    if (memorySources.length === 0) {
        showError('No content to save');
        return;
    }

    try {
        const response = await fetch('/memory/get', {
            method: 'GET',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success && data.combined_text) {
            // Create filename with timestamp
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
            const filename = `lecture-memory-${timestamp}.txt`;

            // Create blob and download
            const blob = new Blob([data.combined_text], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showSuccess('Memory saved successfully');
        } else {
            showError('No content to save');
        }
    } catch (err) {
        console.error('Save memory error:', err);
        showError('Failed to save memory');
    }
}

// Clear all memory
async function clearMemory() {
    if (!confirm('Are you sure you want to clear all sources from memory?')) {
        return;
    }

    try {
        const response = await fetch('/memory/clear', {
            method: 'DELETE',
            credentials: 'include'
        });

        const data = await response.json();

        if (data.success) {
            memorySources = [];
            displayMemorySources();
            updateMemoryUI();
            showSuccess('Memory cleared');
        } else {
            showError('Failed to clear memory');
        }
    } catch (err) {
        console.error('Clear memory error:', err);
        showError('Failed to clear memory');
    }
}

// Update memory UI elements (badge, button state, panel visibility)
function updateMemoryUI() {
    const sourceCount = document.getElementById('sourceCount');
    const memoryPanel = document.getElementById('memoryPanel');
    const processBtn = document.getElementById('processBtn');
    const transcriptInput = document.getElementById('transcriptInput');

    // Update source count badge
    if (sourceCount) {
        const count = memorySources.length;
        sourceCount.textContent = `${count} source${count !== 1 ? 's' : ''}`;
    }

    // Show/hide memory panel based on whether there are sources
    if (memoryPanel) {
        if (memorySources.length > 0) {
            memoryPanel.style.display = 'block';
            memoryMode = true;
        } else {
            memoryPanel.style.display = 'none';
            memoryMode = false;
        }
    }

    // Update main button text and state based on sources
    if (processBtn) {
        const hasTextInput = transcriptInput && transcriptInput.value.trim().length > 0;
        const sourceCount = memorySources.length;

        if (sourceCount === 0) {
            // No sources - regular mode
            processBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Summary';
            processBtn.disabled = !hasTextInput;
        } else if (sourceCount === 1) {
            // 1 source
            processBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Summary from Source';
            processBtn.disabled = false;
        } else {
            // Multiple sources
            processBtn.innerHTML = '<span class="btn-icon">✨</span> Generate Summary from All Sources';
            processBtn.disabled = false;
        }
    }
}

// Generate summary from memory
async function generateFromMemory() {
    if (memorySources.length === 0) {
        showError('Please add sources to memory first');
        return;
    }

    // Use existing processSummary with memory flag
    await processSummary(true);
}

// Helper: Show success message
function showSuccess(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.className = 'success-banner';
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 3000);
}

// ============================================================================
// END MEMORY SYSTEM FUNCTIONS
// ============================================================================

// ============================================================================
// QUICK SAVE TO MEMORY FUNCTIONS
// ============================================================================

// Quick save text input to memory
async function saveTextToMemory() {
    const transcriptInput = document.getElementById('transcriptInput');
    const text = transcriptInput.value.trim();

    if (!text || text.length < 10) {
        showError('Please enter at least 10 characters');
        return;
    }

    try {
        const requestBody = {
            text: text,
            source_type: 'text',
            filename: 'Text Input'
        };

        // Include session_id if we have one
        if (sessionId) {
            requestBody.session_id = sessionId;
        }

        const response = await fetch('/memory/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            // Store session ID for future requests
            if (data.session_id) {
                sessionId = data.session_id;
                console.log('Session ID:', sessionId);
            }

            memorySources.push(data.source_added);
            displayMemorySources();
            updateMemoryUI();

            // Clear input
            transcriptInput.value = '';

            showSuccess(`Added to memory bank! Total sources: ${data.source_count}`);
        } else {
            showError('Failed to add to memory');
        }
    } catch (err) {
        console.error('Save to memory error:', err);
        showError('Failed to save to memory: ' + err.message);
    }
}

// Quick save PDF/document to memory
async function savePDFToMemory() {
    if (!uploadedFileText) {
        showError('No document content to save');
        return;
    }

    const filename = document.getElementById('pdfFilename')?.textContent || 'PDF Document';

    try {
        const requestBody = {
            text: uploadedFileText,
            source_type: 'pdf',
            filename: filename
        };

        // Include session_id if we have one
        if (sessionId) {
            requestBody.session_id = sessionId;
        }

        const response = await fetch('/memory/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            // Store session ID for future requests
            if (data.session_id) {
                sessionId = data.session_id;
                console.log('Session ID:', sessionId);
            }

            memorySources.push(data.source_added);
            displayMemorySources();
            updateMemoryUI();

            // Clear upload
            clearFileUpload('pdf');

            showSuccess(`Added to memory bank! Total sources: ${data.source_count}`);
        } else {
            showError('Failed to add to memory');
        }
    } catch (err) {
        console.error('Save to memory error:', err);
        showError('Failed to save to memory: ' + err.message);
    }
}

// Quick save audio transcription to memory
async function saveAudioToMemory() {
    if (!uploadedFileText) {
        showError('No transcription to save');
        return;
    }

    const filename = document.getElementById('audioFilename')?.textContent || 'Audio Transcription';

    try {
        const requestBody = {
            text: uploadedFileText,
            source_type: 'audio',
            filename: filename
        };

        // Include session_id if we have one
        if (sessionId) {
            requestBody.session_id = sessionId;
        }

        const response = await fetch('/memory/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (data.success) {
            // Store session ID for future requests
            if (data.session_id) {
                sessionId = data.session_id;
                console.log('Session ID:', sessionId);
            }

            memorySources.push(data.source_added);
            displayMemorySources();
            updateMemoryUI();

            // Clear upload
            clearFileUpload('audio');

            showSuccess(`Added to memory bank! Total sources: ${data.source_count}`);
        } else {
            showError('Failed to add to memory');
        }
    } catch (err) {
        console.error('Save to memory error:', err);
        showError('Failed to save to memory: ' + err.message);
    }
}

// ============================================================================
// END QUICK SAVE TO MEMORY FUNCTIONS
// ============================================================================

// Switch input mode (text, pdf, audio)
function switchInputMode(mode) {
    currentInputMode = mode;

    // Update tabs
    document.querySelectorAll('.upload-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.input === mode);
    });

    // Update input modes
    document.getElementById('textInputMode').classList.toggle('hidden', mode !== 'text');
    document.getElementById('pdfInputMode').classList.toggle('hidden', mode !== 'pdf');
    document.getElementById('audioInputMode').classList.toggle('hidden', mode !== 'audio');

    // Clear previous uploads when switching
    if (mode !== 'text') {
        uploadedFileText = null;
    }
}

// Setup drag and drop for documents (PDF, DOCX, PPTX, TXT)
const pdfDropzone = document.getElementById('pdfDropzone');
pdfDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    pdfDropzone.classList.add('dragover');
});

pdfDropzone.addEventListener('dragleave', () => {
    pdfDropzone.classList.remove('dragover');
});

pdfDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    pdfDropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handlePDFFile(files[0]);
    }
});

pdfDropzone.addEventListener('click', () => {
    document.getElementById('pdfFileInput').click();
});

// Setup drag and drop for audio
const audioDropzone = document.getElementById('audioDropzone');
audioDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    audioDropzone.classList.add('dragover');
});

audioDropzone.addEventListener('dragleave', () => {
    audioDropzone.classList.remove('dragover');
});

audioDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    audioDropzone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleAudioFile(files[0]);
    }
});

audioDropzone.addEventListener('click', () => {
    document.getElementById('audioFileInput').click();
});

// Handle document upload from input (PDF, DOCX, PPTX, TXT)
function handlePDFUpload(event) {
    const file = event.target.files[0];
    if (file) {
        handlePDFFile(file);
    }
}

// Handle audio upload from input
function handleAudioUpload(event) {
    const file = event.target.files[0];
    if (file) {
        handleAudioFile(file);
    }
}

// Process document file (PDF, DOCX, PPTX, TXT)
async function handlePDFFile(file) {
    // Validate file type
    const validExtensions = ['.pdf', '.docx', '.pptx', '.txt'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validExtensions.includes(fileExt)) {
        alert('Please upload a PDF, Word, PowerPoint, or Text file');
        return;
    }

    // Validate file size
    const maxSize = appConfig ? appConfig.max_pdf_size_mb * 1024 * 1024 : 50 * 1024 * 1024;
    if (file.size > maxSize) {
        alert(`File is too large. Maximum size: ${maxSize / 1024 / 1024}MB`);
        return;
    }

    // Show progress
    document.getElementById('pdfDropzone').classList.add('hidden');
    document.getElementById('pdfProgress').classList.remove('hidden');

    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/upload_document', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Document upload failed');
        }

        // Store extracted text
        uploadedFileText = data.text;

        // Show preview
        document.getElementById('pdfProgress').classList.add('hidden');
        document.getElementById('pdfPreview').classList.remove('hidden');
        document.getElementById('pdfFilename').textContent = file.name;

        // Show excerpt (first 500 chars)
        const excerpt = data.text.substring(0, 500) + (data.text.length > 500 ? '...' : '');
        document.getElementById('pdfPreviewContent').textContent =
            `Extracted ${data.character_count} characters from ${data.file_type}\n\n${excerpt}`;

        // Populate textarea with extracted text
        document.getElementById('transcriptInput').value = data.text;

        console.log(`${data.file_type} processed successfully`);

    } catch (err) {
        alert('Error processing document: ' + err.message);
        clearFileUpload('pdf');
    }
}

// Process audio file
// Store selected audio file
let selectedAudioFile = null;

async function handleAudioFile(file) {
    // Validate file type
    const validExtensions = ['.mp3', '.wav', '.m4a'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!validExtensions.includes(fileExt)) {
        alert('Please upload an MP3, WAV, or M4A file');
        return;
    }

    // Validate file size
    const maxSize = appConfig ? appConfig.max_audio_size_mb * 1024 * 1024 : 200 * 1024 * 1024;
    if (file.size > maxSize) {
        alert(`Audio file is too large. Maximum size: ${maxSize / 1024 / 1024}MB`);
        return;
    }

    // Store file and show file selected state
    selectedAudioFile = file;
    document.getElementById('audioDropzone').classList.add('hidden');
    document.getElementById('audioFileSelected').classList.remove('hidden');
    document.getElementById('audioFilenameSelected').textContent = file.name;
}

// Start transcription when button is clicked
async function startTranscription() {
    if (!selectedAudioFile) {
        alert('No audio file selected');
        return;
    }

    // Hide file selected, show progress
    document.getElementById('audioFileSelected').classList.add('hidden');
    const progressDiv = document.getElementById('audioProgress');
    progressDiv.classList.remove('hidden');
    progressDiv.classList.add('transcribing');

    try {
        // Upload file with language
        const formData = new FormData();
        formData.append('file', selectedAudioFile);
        formData.append('language', selectedLanguage);

        // Update progress text
        const progressText = document.getElementById('audioProgressText');
        progressText.textContent = 'Starting transcription...';

        // Hide progress, show preview area for live transcription
        progressDiv.classList.add('hidden');
        document.getElementById('audioPreview').classList.remove('hidden');
        document.getElementById('audioFilename').textContent = selectedAudioFile.name;
        const previewContent = document.getElementById('audioPreviewContent');
        previewContent.textContent = 'Preparing transcription...\n\n';

        let fullTranscript = '';
        let characterCount = 0;

        const response = await fetch('/upload_audio_stream', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to start transcription');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Read the stream
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));

                    if (data.status === 'transcribing') {
                        previewContent.innerHTML = `<div class="transcription-status">Transcribing audio... <span class="streaming-indicator">▸</span></div>\n\n`;
                    } else if (data.status === 'segment') {
                        // Add paragraph break if needed
                        if (data.is_paragraph_break && fullTranscript) {
                            fullTranscript += '\n\n';
                        }

                        // Add timestamp if natural break
                        if (data.is_natural_break) {
                            fullTranscript += `${data.timestamp} `;
                        } else {
                            fullTranscript += ' ';
                        }

                        // Add entire segment immediately
                        fullTranscript += data.text;
                        characterCount += data.text.length;

                        // Update display with streaming indicator for current segment
                        const segmentHeader = `<div class="transcription-status">Segment ${data.segment_index + 1}/${data.total_segments} <span class="streaming-indicator">▸</span></div>\n\n`;
                        previewContent.innerHTML = segmentHeader + fullTranscript;

                        // Auto-scroll to bottom
                        previewContent.scrollTop = previewContent.scrollHeight;
                    } else if (data.status === 'complete') {
                        // Store transcribed text
                        uploadedFileText = fullTranscript.trim();

                        // Show final transcription without header
                        previewContent.textContent = fullTranscript.trim();

                        // Populate textarea
                        document.getElementById('transcriptInput').value = fullTranscript.trim();

                        console.log('Audio transcribed successfully');
                    } else if (data.status === 'error') {
                        throw new Error(data.message);
                    }
                }
            }
        }

    } catch (err) {
        console.error('Transcription error:', err);
        alert('Error transcribing audio: ' + err.message);
        clearFileUpload('audio');
    }
}

// Clear audio file selection (before transcription)
function clearAudioSelection() {
    selectedAudioFile = null;
    document.getElementById('audioFileInput').value = '';
    document.getElementById('audioFileSelected').classList.add('hidden');
    document.getElementById('audioDropzone').classList.remove('hidden');
}

// Clear file upload
function clearFileUpload(type) {
    uploadedFileText = null;

    if (type === 'pdf') {
        document.getElementById('pdfFileInput').value = '';
        document.getElementById('pdfDropzone').classList.remove('hidden');
        document.getElementById('pdfProgress').classList.add('hidden');
        document.getElementById('pdfPreview').classList.add('hidden');
    } else if (type === 'audio') {
        selectedAudioFile = null;
        document.getElementById('audioFileInput').value = '';
        document.getElementById('audioDropzone').classList.remove('hidden');
        document.getElementById('audioFileSelected').classList.add('hidden');
        document.getElementById('audioProgress').classList.add('hidden');
        document.getElementById('audioPreview').classList.add('hidden');
    }

    // Clear textarea
    document.getElementById('transcriptInput').value = '';
}

// Language change handler
function changeLanguage() {
    const select = document.getElementById('languageSelect');
    selectedLanguage = select.value;
    console.log('Language changed to:', selectedLanguage);
    
    // If there are existing summaries or Q&A, notify user they need to regenerate
    if (allSummaries || document.getElementById('qaHistory').children.length > 0) {
        const languageNames = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese',
            'ru': 'Russian'
        };
        
        const notification = document.createElement('div');
        notification.className = 'language-notification';
        notification.textContent = `Language changed to ${languageNames[selectedLanguage]}. Generate new summaries or ask questions in this language.`;
        notification.style.cssText = 'background: var(--primary-light); color: var(--primary); padding: 12px; border-radius: 8px; margin: 20px 0; text-align: center; font-weight: 500;';
        
        document.querySelector('.controls-card').appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Store quiz data

// Get knowledge level label (kept for compatibility, now uses getLevelLabel)
function getKnowledgeLevelLabel(level) {
    const numericLevel = getLevel(Math.round(level * 100));
    return getLevelLabel(numericLevel) + ' Level';
}

// Adaptive quiz state
let adaptiveQuizState = {
    currentDifficulty: 0,  // Start at beginner level
    questionHistory: [],
    correctCount: 0,
    incorrectCount: 0,
    questionCount: 0
};

// Start adaptive quiz
async function startQuiz() {
    const quizContainer = document.getElementById('quizContainer');
    const result = document.getElementById('result');
    const loading = document.getElementById('loading');

    // Reset adaptive quiz state
    adaptiveQuizState = {
        currentDifficulty: 0,  // Start at complete beginner
        questionHistory: [],
        correctCount: 0,
        incorrectCount: 0,
        questionCount: 0
    };

    // Hide summary, show quiz
    result.style.display = 'none';
    quizContainer.style.display = 'block';

    // Scroll to quiz
    setTimeout(() => {
        quizContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);

    // Generate and show first question
    await generateNextAdaptiveQuestion();
}

// Generate next adaptive question
async function generateNextAdaptiveQuestion() {
    const quizContent = document.getElementById('quizContent');
    const loading = document.getElementById('loading');

    // Show loading
    loading.style.display = 'block';
    quizContent.innerHTML = '<div class="loading-message">Generating question...</div>';

    try {
        const requestBody = {
            difficulty_level: adaptiveQuizState.currentDifficulty,
            previous_questions: adaptiveQuizState.questionHistory
        };

        // If we're in memory mode, send session_id instead of transcript
        if (memorySources.length > 0 && sessionId) {
            requestBody.session_id = sessionId;
            requestBody.use_memory = true;
        } else {
            requestBody.transcript = currentTranscript;
        }

        const response = await fetch('/generate_adaptive_question', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Question generation failed');
        }

        const question = data.question;
        adaptiveQuizState.questionHistory.push(question);
        adaptiveQuizState.questionCount++;

        // Render the question
        renderAdaptiveQuestion(question);

    } catch (err) {
        alert('Error generating question: ' + err.message);
        quizContent.innerHTML = '<div class="error-message">Failed to generate question.</div>';
    } finally {
        loading.style.display = 'none';
    }
}

// Render adaptive question
function renderAdaptiveQuestion(question) {
    const quizContent = document.getElementById('quizContent');
    const difficultyNames = ['Complete Beginner', 'Beginner', 'Intermediate', 'Advanced', 'Expert'];

    quizContent.innerHTML = `
        <div class="adaptive-quiz-info">
            <div class="quiz-progress">
                <span class="difficulty-badge">Level: ${difficultyNames[adaptiveQuizState.currentDifficulty]}</span>
                <span class="question-counter">Question ${adaptiveQuizState.questionCount}</span>
                <span class="score-display">✓ ${adaptiveQuizState.correctCount} | ✗ ${adaptiveQuizState.incorrectCount}</span>
            </div>
        </div>
        <div class="quiz-question">
            <h3>Question ${adaptiveQuizState.questionCount}</h3>
            <p>${question}</p>
            <textarea id="adaptive-answer" placeholder="Type your answer here..." rows="5"></textarea>
            <button class="submit-answer-btn" onclick="submitAdaptiveAnswer()">Submit Answer</button>
            <div class="feedback" id="adaptive-feedback">
                <div class="feedback-content" id="adaptive-feedback-content"></div>
            </div>
        </div>
    `;
}

// Submit adaptive answer
async function submitAdaptiveAnswer() {
    const answerTextarea = document.getElementById('adaptive-answer');
    const answer = answerTextarea.value.trim();
    const submitBtn = answerTextarea.nextElementSibling;
    const feedbackDiv = document.getElementById('adaptive-feedback');
    const feedbackContent = document.getElementById('adaptive-feedback-content');

    if (!answer) {
        alert('Please write an answer first');
        return;
    }

    // Disable button and textarea
    submitBtn.disabled = true;
    answerTextarea.disabled = true;
    submitBtn.textContent = 'Evaluating...';

    try {
        const currentQuestion = adaptiveQuizState.questionHistory[adaptiveQuizState.questionHistory.length - 1];
        const formData = new FormData();
        formData.append('question', currentQuestion);
        formData.append('answer', answer);
        formData.append('knowledge_level', adaptiveQuizState.currentDifficulty);

        // If we're in memory mode, send session info instead of transcript
        if (memorySources.length > 0 && sessionId) {
            formData.append('session_id', sessionId);
            formData.append('use_memory', 'true');
        } else {
            formData.append('transcript', currentTranscript);
        }

        const response = await fetch('/evaluate_answer', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Evaluation failed');
        }

        // Show feedback
        const evaluation = data.evaluation;
        feedbackDiv.className = 'feedback ' + evaluation.score;
        feedbackContent.innerHTML = `
            <div class="feedback-score">${evaluation.score === 'correct' ? '✓ Correct!' : evaluation.score === 'partial' ? '◐ Partially Correct' : '✗ Incorrect'}</div>
            <div class="feedback-text">${evaluation.feedback}</div>
        `;
        feedbackDiv.style.display = 'block';

        // Update score tracking
        if (evaluation.score === 'correct') {
            adaptiveQuizState.correctCount++;
        } else {
            adaptiveQuizState.incorrectCount++;
        }

        // Determine next difficulty level
        let nextDifficulty = adaptiveQuizState.currentDifficulty;

        if (evaluation.score === 'correct') {
            // Correct answer - increase difficulty (max 4)
            nextDifficulty = Math.min(4, adaptiveQuizState.currentDifficulty + 1);
        } else if (evaluation.score === 'incorrect') {
            // Incorrect answer - this is their knowledge ceiling
            // Stay at this level or go down one
            nextDifficulty = Math.max(0, adaptiveQuizState.currentDifficulty - 1);
        } else {
            // Partial - stay at same level
            nextDifficulty = adaptiveQuizState.currentDifficulty;
        }

        adaptiveQuizState.currentDifficulty = nextDifficulty;

        // Add "Next Question" button
        const nextButton = document.createElement('button');
        nextButton.className = 'primary-btn';
        nextButton.style.marginTop = '20px';
        nextButton.textContent = adaptiveQuizState.questionCount >= 5 ? 'Finish Quiz' : 'Next Question';
        nextButton.onclick = async () => {
            if (adaptiveQuizState.questionCount >= 5) {
                showAdaptiveQuizSummary();
            } else {
                await generateNextAdaptiveQuestion();
            }
        };
        feedbackDiv.appendChild(nextButton);

        submitBtn.textContent = '✓ Submitted';

    } catch (err) {
        alert('Error evaluating answer: ' + err.message);
        submitBtn.disabled = false;
        answerTextarea.disabled = false;
        submitBtn.textContent = 'Submit Answer';
    }
}

// Show adaptive quiz summary
function showAdaptiveQuizSummary() {
    const quizContent = document.getElementById('quizContent');
    const difficultyNames = ['Complete Beginner', 'Beginner', 'Intermediate', 'Advanced', 'Expert'];
    const finalLevel = adaptiveQuizState.currentDifficulty;

    quizContent.innerHTML = `
        <div class="quiz-summary">
            <h2>🎯 Quiz Complete!</h2>
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-value">${adaptiveQuizState.correctCount}</div>
                    <div class="stat-label">Correct</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${adaptiveQuizState.incorrectCount}</div>
                    <div class="stat-label">Incorrect</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${difficultyNames[finalLevel]}</div>
                    <div class="stat-label">Final Level</div>
                </div>
            </div>
            <div class="summary-message">
                <p><strong>Your Knowledge Level:</strong> ${difficultyNames[finalLevel]}</p>
                <p>The quiz adapted to find your current understanding. ${
                    finalLevel === 4 ? 'Excellent! You demonstrated expert-level knowledge.' :
                    finalLevel === 3 ? 'Great! You have advanced understanding of this topic.' :
                    finalLevel === 2 ? 'Good! You have solid intermediate knowledge.' :
                    finalLevel === 1 ? 'You have beginner-level understanding. Keep learning!' :
                    'Focus on the basics to build a stronger foundation.'
                }</p>
            </div>
            <button class="primary-btn" onclick="backToSummary()">Back to Summary</button>
            <button class="secondary-btn" onclick="startQuiz()">Try Again</button>
        </div>
    `;
}

// Render quiz questions
function renderQuiz() {
    const quizContent = document.getElementById('quizContent');
    quizContent.innerHTML = '';
    
    quizQuestions.forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'quiz-question';
        questionDiv.innerHTML = `
            <h3>Question ${index + 1}</h3>
            <p>${question}</p>
            <textarea id="answer-${index}" placeholder="Type your answer here..."></textarea>
            <button class="submit-answer-btn" onclick="submitAnswer(${index})">Submit Answer</button>
            <div class="feedback" id="feedback-${index}">
                <div class="feedback-content" id="feedback-content-${index}"></div>
            </div>
        `;
        quizContent.appendChild(questionDiv);
    });
}

// Submit an answer
async function submitAnswer(questionIndex) {
    const answerTextarea = document.getElementById(`answer-${questionIndex}`);
    const answer = answerTextarea.value.trim();
    const submitBtn = answerTextarea.nextElementSibling;
    const feedbackDiv = document.getElementById(`feedback-${questionIndex}`);
    const feedbackContent = document.getElementById(`feedback-content-${questionIndex}`);
    
    if (!answer) {
        alert('Please write an answer first');
        return;
    }
    
    // Disable button and textarea
    submitBtn.disabled = true;
    answerTextarea.disabled = true;
    submitBtn.textContent = 'Evaluating...';
    
    try {
        const currentLevel = getLevel(slider.value);
        const formData = new FormData();
        formData.append('question', quizQuestions[questionIndex]);
        formData.append('answer', answer);
        formData.append('transcript', currentTranscript);
        formData.append('knowledge_level', currentLevel);
        
        const response = await fetch('/evaluate_answer', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Evaluation failed');
        }
        
        // Show feedback
        const evaluation = data.evaluation;
        feedbackDiv.className = 'feedback ' + evaluation.score;
        feedbackContent.textContent = evaluation.feedback;
        feedbackDiv.style.display = 'block';
        
        submitBtn.textContent = '✓ Submitted';
        
    } catch (err) {
        alert('Error evaluating answer: ' + err.message);
        submitBtn.disabled = false;
        answerTextarea.disabled = false;
        submitBtn.textContent = 'Submit Answer';
    }
}

// Back to summary
function backToSummary() {
    const quizContainer = document.getElementById('quizContainer');
    const result = document.getElementById('result');
    
    quizContainer.style.display = 'none';
    result.style.display = 'block';
    
    result.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Q&A Functions
function toggleQA() {
    const qaSection = document.getElementById('qaSection');
    const transcriptInput = document.getElementById('transcriptInput');
    
    if (!transcriptInput.value.trim()) {
        alert('Please enter a lecture transcript first');
        return;
    }
    
    if (qaSection.style.display === 'none' || !qaSection.style.display) {
        qaSection.style.display = 'block';
        qaSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        qaSection.style.display = 'none';
    }
}

async function askQuestion() {
    const questionInput = document.getElementById('questionInput');
    const transcriptInput = document.getElementById('transcriptInput');
    const askBtn = document.getElementById('askBtn');
    const qaHistory = document.getElementById('qaHistory');
    
    const question = questionInput.value.trim();
    const transcript = transcriptInput.value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    if (!transcript) {
        alert('Please enter a lecture transcript first');
        return;
    }
    
    // Get current knowledge level
    const currentLevel = getLevel(slider.value);
    
    // Disable button
    askBtn.disabled = true;
    askBtn.innerHTML = '<span>⏳</span> Thinking...';
    
    try {
        const formData = new FormData();
        formData.append('transcript', transcript);
        formData.append('question', question);
        formData.append('knowledge_level', currentLevel);
        formData.append('language', selectedLanguage);
        
        const response = await fetch('/ask_question', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to get answer');
        }
        
        // Add to history
        const exchangeDiv = document.createElement('div');
        exchangeDiv.className = 'qa-exchange';
        exchangeDiv.innerHTML = `
            <div class="qa-question">${question}</div>
            <div class="qa-answer">${data.answer}</div>
        `;
        
        qaHistory.insertBefore(exchangeDiv, qaHistory.firstChild);
        
        // Clear input
        questionInput.value = '';
        
        // Scroll to new answer
        setTimeout(() => {
            exchangeDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        askBtn.disabled = false;
        askBtn.innerHTML = '<span>💡</span> Get Answer';
    }
}

// Process summary - now with streaming!
async function processSummary(useMemory = false) {
    const transcriptInput = document.getElementById('transcriptInput');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const error = document.getElementById('error');
    const processBtn = document.getElementById('processBtn');

    // Reset displays
    result.style.display = 'none';
    error.style.display = 'none';
    document.getElementById('quizContainer').style.display = 'none';

    // Validate input (skip if using memory)
    if (!useMemory && !transcriptInput.value.trim()) {
        error.textContent = 'Please enter a transcript first';
        error.style.display = 'block';
        return;
    }

    // Validate memory mode
    if (useMemory && memorySources.length === 0) {
        error.textContent = 'Please add sources to memory first';
        error.style.display = 'block';
        return;
    }

    // Store transcript for quiz (will be fetched from memory if needed)
    if (!useMemory) {
        currentTranscript = transcriptInput.value;
    }

    // Show loading with streaming message
    loading.style.display = 'block';
    loading.querySelector('p').textContent = useMemory ?
        'Generating summaries from all sources - watch them appear live!' :
        'Generating summaries - watch them appear live!';
    processBtn.disabled = true;

    // Initialize summaries storage
    allSummaries = {
        '0': '',
        '1': '',
        '2': '',
        '3': '',
        '4': ''
    };
    let currentStreamLevel = null;
    let fullResponse = '';

    try {
        // Get current knowledge level from slider (0-100 to 0.0-1.0)
        const knowledgeSlider = document.getElementById('knowledgeSlider');
        const knowledgeLevel = parseInt(knowledgeSlider.value) / 100;

        const requestBody = {
            use_memory: useMemory,
            language: selectedLanguage,
            knowledge_level: knowledgeLevel
        };

        // Only include transcript if not using memory
        if (!useMemory) {
            requestBody.transcript = transcriptInput.value;
        }

        // Include session_id if we have one (for memory mode)
        if (sessionId) {
            requestBody.session_id = sessionId;
        }

        const response = await fetch('/process_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Show result container immediately
        result.style.display = 'block';
        document.getElementById('resultContent').innerHTML = '<div class="streaming-placeholder">Generating summaries...</div>';
        
        // Scroll to results
        setTimeout(() => {
            result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            console.log('Received chunk:', chunk.substring(0, 100));
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.substring(6);
                    if (!jsonStr.trim()) continue;
                    
                    try {
                        const data = JSON.parse(jsonStr);
                        console.log('Parsed data:', data.type, data);
                        
                        if (data.type === 'test') {
                            console.log('TEST MESSAGE:', data.message);
                            // Hide loading as soon as stream starts
                            loading.style.display = 'none';
                        } else if (data.type === 'level_start') {
                            currentStreamLevel = data.level;
                            console.log('Starting level:', currentStreamLevel);
                        } else if (data.type === 'content') {
                            // Hide loading on first content
                            if (loading.style.display !== 'none') {
                                loading.style.display = 'none';
                            }
                            
                            // Store content for the specific level
                            const level = data.level;
                            if (level !== null && level !== undefined) {
                                allSummaries[level.toString()] += data.text;
                            }
                            
                            // Update display for current slider position
                            const currentLevel = getLevel(slider.value);
                            if (allSummaries[currentLevel.toString()]) {
                                updateStreamingDisplay(currentLevel);
                            }
                        } else if (data.type === 'summaries') {
                            // Final summaries received
                            allSummaries = {
                                '0': data.data[0] || '',
                                '1': data.data[1] || '',
                                '2': data.data[2] || '',
                                '3': data.data[3] || '',
                                '4': data.data[4] || ''
                            };
                            console.log('Final summaries received');
                        } else if (data.type === 'complete') {
                            console.log('Streaming complete!');
                            
                            // Display final version
                            const currentLevel = getLevel(slider.value);
                            displaySummary(currentLevel);
                        } else if (data.type === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        console.error('Error parsing chunk:', e, jsonStr);
                    }
                }
            }
        }
        
        loading.style.display = 'none';
        
    } catch (err) {
        error.textContent = 'Error: ' + err.message;
        error.style.display = 'block';
        result.style.display = 'none';
        loading.style.display = 'none';
    } finally {
        processBtn.disabled = false;
        loading.querySelector('p').textContent = 'Generating your personalized summary...';
    }
}

function updateStreamingDisplay(level) {
    const summary = allSummaries[level.toString()];
    if (!summary) return;

    // Update badge
    document.getElementById('knowledgeBadge').textContent = getLevelLabel(level) + ' Level';

    // Parse and display (even partial content) - NO ANIMATIONS during streaming
    const htmlContent = parseMarkdownToHTML(summary);
    const resultContent = document.getElementById('resultContent');
    resultContent.innerHTML = htmlContent;

    // Remove animations from streaming sections
    const sections = resultContent.querySelectorAll('.summary-section');
    sections.forEach((section, index) => {
        section.style.animation = 'none';
        section.style.opacity = '1';
        section.style.transform = 'none';

        // Add streaming indicator to the section being generated
        const h2 = section.querySelector('h2');
        if (h2 && index === sections.length - 1) {
            // This is the last (currently generating) section
            if (!h2.querySelector('.streaming-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'streaming-indicator';
                indicator.textContent = ' ▸';
                h2.appendChild(indicator);
            }
        } else {
            // Remove indicator from completed sections
            const indicator = h2?.querySelector('.streaming-indicator');
            if (indicator) {
                indicator.remove();
            }
        }
    });
}

function parseFinalSummaries(fullResponse) {
    // Parse the complete response into 5 separate summaries
    const parts = fullResponse.split('---LEVEL_');
    
    for (let i = 1; i < parts.length; i++) {
        const part = parts[i];
        const lines = part.split('\n', 1);
        if (lines.length < 1) continue;
        
        const levelNum = lines[0].replace('---', '').trim();
        const content = part.substring(lines[0].length).trim();
        
        allSummaries[levelNum] = content;
    }
    
    console.log('Parsed summaries:', Object.keys(allSummaries));
}