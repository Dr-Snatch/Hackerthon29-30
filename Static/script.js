// Initialize slider
const slider = document.getElementById('knowledgeSlider');
const valueDisplay = document.getElementById('knowledgeValue');
const labelDisplay = document.getElementById('knowledgeLabel');

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
    const exampleText = "Today we're going to talk about machine learning, specifically neural networks. Neural networks are computing systems inspired by biological neural networks in animal brains. They consist of interconnected nodes called neurons organized in layers. The input layer receives data, hidden layers process it through weighted connections, and the output layer produces results. Each connection has a weight that gets adjusted during training through a process called backpropagation. This allows the network to learn patterns from data. Common applications include image recognition, natural language processing, and predictive analytics. The key advantage is that neural networks can learn complex non-linear relationships in data without explicit programming of rules.";
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

// Get knowledge level label (kept for compatibility, now uses getLevelLabel)
function getKnowledgeLevelLabel(level) {
    const numericLevel = getLevel(Math.round(level * 100));
    return getLevelLabel(numericLevel) + ' Level';
}

// Start quiz
async function startQuiz() {
    const quizContainer = document.getElementById('quizContainer');
    const result = document.getElementById('result');
    const loading = document.getElementById('loading');
    
    // Get current knowledge level
    const currentLevel = getLevel(slider.value);
    
    // Show loading
    loading.style.display = 'block';
    
    try {
        const formData = new FormData();
        formData.append('transcript', currentTranscript);
        formData.append('knowledge_level', currentLevel);
        
        const response = await fetch('/generate_quiz', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Quiz generation failed');
        }
        
        quizQuestions = data.questions;
        
        // Hide summary, show quiz
        result.style.display = 'none';
        quizContainer.style.display = 'block';
        
        // Render quiz questions
        renderQuiz();
        
        // Scroll to quiz
        setTimeout(() => {
            quizContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
        
    } catch (err) {
        alert('Error generating quiz: ' + err.message);
    } finally {
        loading.style.display = 'none';
    }
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

// Process summary - now with streaming!
async function processSummary() {
    const transcriptInput = document.getElementById('transcriptInput');
    const loading = document.getElementById('loading');
    const result = document.getElementById('result');
    const error = document.getElementById('error');
    const processBtn = document.getElementById('processBtn');
    
    // Reset displays
    result.style.display = 'none';
    error.style.display = 'none';
    document.getElementById('quizContainer').style.display = 'none';
    
    // Validate input
    if (!transcriptInput.value.trim()) {
        error.textContent = 'Please enter a transcript first';
        error.style.display = 'block';
        return;
    }
    
    // Store transcript for quiz
    currentTranscript = transcriptInput.value;
    
    // Show loading with streaming message
    loading.style.display = 'block';
    loading.querySelector('p').textContent = 'Generating summaries - watch them appear live!';
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
        const response = await fetch('/process_stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transcript: transcriptInput.value
            })
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
    sections.forEach(section => {
        section.style.animation = 'none';
        section.style.opacity = '1';
        section.style.transform = 'none';
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