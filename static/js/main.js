/**
 * main.js
 * 
 * Client-side script handling editor, templates loading, API integration,
 * animations, collapsible segments, copy summaries, and JSON/PDF audit exports.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const textarea = document.getElementById('code-textarea');
    const lineGutter = document.getElementById('line-gutter');
    const btnAnalyze = document.getElementById('btn-analyze');
    const analyzeSpinner = document.getElementById('analyze-spinner');
    const statusMessage = document.getElementById('status-message');
    const errorBanner = document.getElementById('error-banner');
    const errorText = document.getElementById('error-text');
    
    // Results DOM Elements
    const resultsPanel = document.getElementById('results-panel');
    const timeComplexityVal = document.getElementById('time-complexity-value');
    const spaceComplexityVal = document.getElementById('space-complexity-value');
    const explanationText = document.getElementById('complexity-explanation-text');
    const patternsContainer = document.getElementById('patterns-container');
    const patternsEmptyState = document.getElementById('patterns-empty-state');
    const suggestionsContainer = document.getElementById('suggestions-container');
    const suggestionsEmptyState = document.getElementById('suggestions-empty-state');
    
    // Developer Upgrades DOM elements
    const confidenceBadge = document.getElementById('confidence-badge');
    const cyclomaticVal = document.getElementById('cyclomatic-value');
    const cyclomaticRiskBadge = document.getElementById('cyclomatic-risk-badge');
    const ccIconWrapper = document.getElementById('cc-icon-wrapper');
    const smellsContainer = document.getElementById('smells-container');
    const smellsEmptyState = document.getElementById('smells-empty-state');
    
    // Quality Scores Elements
    const overallScoreText = document.getElementById('overall-score-text');
    const scoreCircleBar = document.getElementById('score-circle-bar');
    const scoreValEfficiency = document.getElementById('score-val-efficiency');
    const scoreValReadability = document.getElementById('score-val-readability');
    const scoreValMaintainability = document.getElementById('score-val-maintainability');
    const scoreValNaming = document.getElementById('score-val-naming');
    const barEfficiency = document.getElementById('bar-fill-efficiency');
    const barReadability = document.getElementById('bar-fill-readability');
    const barMaintainability = document.getElementById('bar-fill-maintainability');
    const barNaming = document.getElementById('bar-fill-naming');
    
    // Stats DOM Elements
    const statLinesTotal = document.getElementById('stat-lines-total');
    const statLinesCode = document.getElementById('stat-lines-code');
    const statLinesComments = document.getElementById('stat-lines-comments');
    const statFunctions = document.getElementById('stat-functions');
    const statLoops = document.getElementById('stat-loops');
    const statRecursion = document.getElementById('stat-recursion');
    const statIfs = document.getElementById('stat-ifs');
    const statVariables = document.getElementById('stat-variables');

    // Action buttons
    const btnCopy = document.getElementById('btn-copy');
    const btnExportJson = document.getElementById('btn-export-json');
    const btnExportPdf = document.getElementById('btn-export-pdf');

    // Keep track of last analysis response for report exports
    let lastAnalysisReport = null;

    // Templates Library
    const templates = {
        'binary-search': `// C++ Binary Search Implementation
// Time Complexity: O(log n) | Space Complexity: O(1)
int binarySearch(int arr[], int n, int target) {
    int low = 0;
    int high = n - 1;
    
    while (low <= high) {
        int mid = low + (high - low) / 2;
        
        if (arr[mid] == target) {
            return mid; // Found target index
        }
        
        if (arr[mid] < target) {
            low = mid + 1; // Discard left half
        } else {
            high = mid - 1; // Discard right half
        }
    }
    return -1; // Target not found
}`,

        'bubble-sort': `// C++ Bubble Sort Implementation
// Time Complexity: O(n²) | Space Complexity: O(1)
void bubbleSort(vector<int>& arr) {
    int n = arr.size();
    
    // Outer loop runs n times
    for (int i = 0; i < n - 1; i++) {
        // Inner loop runs n - i - 1 times
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                // Swap elements out of order
                swap(arr[j], arr[j + 1]);
            }
        }
    }
}`,

        'fibonacci': `// C++ Naive Recursive Fibonacci
// Time Complexity: O(2^n) | Space Complexity: O(n) call stack
int fibonacci(int n) {
    if (n <= 1) {
        return n; // Base case
    }
    
    // Exponential branching - triggers multiple recursive calls
    return fibonacci(n - 1) + fibonacci(n - 2);
}`,

        'nested-loops': `// C++ Matrix Multiplication (Three Nested Loops)
// Time Complexity: O(n³) | Space Complexity: O(n²)
void multiplyMatrices(vector<vector<int>>& A, vector<vector<int>>& B, vector<vector<int>>& C, int n) {
    // Outer loop runs n times
    for (int i = 0; i < n; i++) {
        // Second loop runs n times
        for (int j = 0; j < n; j++) {
            C[i][j] = 0;
            // Third loop runs n times
            for (int k = 0; k < n; k++) {
                C[i][j] += A[i][k] * B[k][j];
            }
        }
    }
}`,

        'memoization': `// Recursive paths count. Highly inefficient without memoization.
// Time Complexity: O(2^n) | Space Complexity: O(n)
int countPaths(int r, int c, int n, int m) {
    // Reached destination
    if (r == n - 1 && c == m - 1) {
        return 1;
    }
    
    // Out of bounds
    if (r >= n || c >= m) {
        return 0;
    }
    
    // Double recursive branches
    return countPaths(r + 1, c, n, m) + countPaths(r, c + 1, n, m);
}`
    };

    /* ==========================================================================
       Editor Functionality (Lines & Sync)
       ========================================================================== */
    
    function updateLineNumbers() {
        const lines = textarea.value.split('\n');
        const lineCount = lines.length;
        
        let gutterContent = '';
        for (let i = 1; i <= lineCount; i++) {
            gutterContent += i + '\n';
        }
        lineGutter.textContent = gutterContent;
    }

    // Initialize line numbers
    updateLineNumbers();

    // Update numbers on input
    textarea.addEventListener('input', updateLineNumbers);

    // Sync scrolling of textarea and line gutter
    textarea.addEventListener('scroll', () => {
        lineGutter.scrollTop = textarea.scrollTop;
    });

    // Handle Tab key inside textarea: insert 4 spaces
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const val = textarea.value;
            
            textarea.value = val.substring(0, start) + '    ' + val.substring(end);
            
            // Put caret in right position (4 spaces ahead)
            textarea.selectionStart = textarea.selectionEnd = start + 4;
            
            // Trigger input updates
            updateLineNumbers();
        }
    });

    /* ==========================================================================
       Collapsible Cards Implementation
       ========================================================================== */
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    collapsibleHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const card = header.closest('.collapsible-card');
            const toggleButton = header.querySelector('.btn-toggle');
            
            const isCollapsed = card.classList.toggle('collapsed');
            
            if (toggleButton) {
                toggleButton.setAttribute('aria-expanded', !isCollapsed);
            }
        });
    });

    /* ==========================================================================
       Template Loading
       ========================================================================== */
    function loadTemplate(key) {
        if (templates[key]) {
            textarea.value = templates[key];
            updateLineNumbers();
            
            // Reset status
            statusMessage.textContent = 'Template loaded. Ready to analyze.';
            
            // Hide previous results and errors
            resultsPanel.style.display = 'none';
            errorBanner.style.display = 'none';
            
            // Scroll to editor
            textarea.focus();
        }
    }

    // Setup template event listeners
    document.getElementById('template-binary-search').addEventListener('click', () => loadTemplate('binary-search'));
    document.getElementById('template-bubble-sort').addEventListener('click', () => loadTemplate('bubble-sort'));
    document.getElementById('template-fibonacci').addEventListener('click', () => loadTemplate('fibonacci'));
    document.getElementById('template-nested-loops').addEventListener('click', () => loadTemplate('nested-loops'));
    document.getElementById('template-memoization').addEventListener('click', () => loadTemplate('memoization'));

    // Prepopulate with a template to start with
    loadTemplate('binary-search');

    /* ==========================================================================
       Static Analysis Fetch Request
       ========================================================================== */
    btnAnalyze.addEventListener('click', async () => {
        const code = textarea.value;
        
        if (!code.trim()) {
            showError('Please paste or write some C++ code before running the analyzer.');
            return;
        }

        // Setup loading states
        errorBanner.style.display = 'none';
        resultsPanel.style.display = 'none';
        btnAnalyze.disabled = true;
        analyzeSpinner.style.display = 'inline-block';
        statusMessage.textContent = 'Parsing and calculating code structures...';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code: code })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Server returned an error status.');
            }

            // Cache report for exports
            lastAnalysisReport = data;

            // Success: render analytics
            renderResults(data);
            statusMessage.textContent = 'Analysis complete.';
            
        } catch (err) {
            showError(err.message);
            statusMessage.textContent = 'Analysis failed.';
        } finally {
            btnAnalyze.disabled = false;
            analyzeSpinner.style.display = 'none';
        }
    });

    /* ==========================================================================
       Render Results DOM Update
       ========================================================================== */
    function renderResults(data) {
        // Show results panel
        resultsPanel.style.display = 'flex';
        
        // 1. Time / Space / CC metrics
        timeComplexityVal.textContent = data.time_complexity;
        spaceComplexityVal.textContent = data.space_complexity;
        confidenceBadge.textContent = `${data.confidence_score}% Confidence`;
        
        // Cyclomatic Complexity
        const ccVal = data.cyclomatic_complexity.overall_value;
        const ccRisk = data.cyclomatic_complexity.risk_level;
        cyclomaticVal.textContent = ccVal;
        cyclomaticRiskBadge.textContent = ccRisk;
        
        // Setup CC Risk badge class
        cyclomaticRiskBadge.className = 'risk-badge';
        if (ccRisk === 'Low Risk') {
            cyclomaticRiskBadge.classList.add('badge-low');
        } else if (ccRisk === 'Moderate Risk') {
            cyclomaticRiskBadge.classList.add('badge-mod');
        } else if (ccRisk === 'High Risk') {
            cyclomaticRiskBadge.classList.add('badge-high');
        } else {
            cyclomaticRiskBadge.classList.add('badge-ext');
        }
        
        // 2. Animate Circular Score Bar
        const score = data.quality_scores.overall;
        overallScoreText.textContent = score;
        
        // SVG circle radius is 58, perimeter ~364.4
        const circumference = 58 * 2 * Math.PI;
        scoreCircleBar.style.strokeDasharray = circumference;
        const offset = circumference - (score / 100) * circumference;
        scoreCircleBar.style.strokeDashoffset = offset;
        
        // 3. Linear Quality Meters
        scoreValEfficiency.textContent = `${data.quality_scores.efficiency}%`;
        scoreValReadability.textContent = `${data.quality_scores.readability}%`;
        scoreValMaintainability.textContent = `${data.quality_scores.maintainability}%`;
        scoreValNaming.textContent = `${data.quality_scores.naming}%`;
        
        barEfficiency.style.width = `${data.quality_scores.efficiency}%`;
        barReadability.style.width = `${data.quality_scores.readability}%`;
        barMaintainability.style.width = `${data.quality_scores.maintainability}%`;
        barNaming.style.width = `${data.quality_scores.naming}%`;

        // 4. Statistics
        statLinesTotal.textContent = data.stats.lines_total;
        statLinesCode.textContent = data.stats.lines_code;
        statLinesComments.textContent = data.stats.lines_comment;
        statFunctions.textContent = data.stats.functions_count;
        statLoops.textContent = data.stats.loops_count;
        statRecursion.textContent = data.stats.recursive_calls;
        statIfs.textContent = data.stats.if_statements;
        statVariables.textContent = data.stats.variables_count;

        // 5. Patterns Identified
        patternsContainer.innerHTML = '';
        if (data.patterns && data.patterns.length > 0) {
            patternsEmptyState.style.display = 'none';
            data.patterns.forEach(pattern => {
                const badge = document.createElement('span');
                badge.className = 'pattern-badge';
                badge.textContent = pattern;
                patternsContainer.appendChild(badge);
            });
        } else {
            patternsEmptyState.style.display = 'block';
        }

        // 6. Complexity Explanation text
        // Expand explanation of why complexity was chosen
        let trace = data.explanation;
        // Append Cyclomatic Complexity detail
        trace += `\n\n=== Cyclomatic Complexity Risk Breakdown ===\n`;
        trace += `Overall Risk Level: ${data.cyclomatic_complexity.risk_level} (${data.cyclomatic_complexity.explanation})\n`;
        data.cyclomatic_complexity.details.forEach(func => {
            trace += `- Function \`${func.name}\` (CC: ${func.complexity} - ${func.risk})\n`;
            if (func.breakdown && func.breakdown.length > 0) {
                trace += `  Branches: ${func.breakdown.join(', ')}\n`;
            }
        });
        explanationText.textContent = trace;

        // 7. Render Code Smells
        smellsContainer.innerHTML = '';
        if (data.code_smells && data.code_smells.length > 0) {
            smellsEmptyState.style.display = 'none';
            data.code_smells.forEach(smell => {
                const item = document.createElement('div');
                item.className = 'smell-item';
                
                // Assign severity class
                const severity = smell.severity.toLowerCase(); // high, medium, low
                if (severity === 'high') {
                    item.classList.add('smell-high');
                } else if (severity === 'medium') {
                    item.classList.add('smell-med');
                } else {
                    item.classList.add('smell-low');
                }
                
                const badgeClass = `smell-badge smell-badge-${severity}`;
                const icon = severity === 'high' ? '🚨' : (severity === 'medium' ? '⚠️' : '🔍');
                
                item.innerHTML = `
                    <div class="smell-icon">${icon}</div>
                    <div class="smell-details">
                        <div class="smell-type-line">
                            <span class="smell-type">${smell.type}</span>
                            <span class="${badgeClass}">${smell.severity} severity</span>
                        </div>
                        <span class="smell-details-text">${smell.details}</span>
                    </div>
                `;
                smellsContainer.appendChild(item);
            });
        } else {
            smellsEmptyState.style.display = 'flex';
        }

        // 8. Optimization Suggestions
        suggestionsContainer.innerHTML = '';
        if (data.suggestions && data.suggestions.length > 0) {
            suggestionsEmptyState.style.display = 'none';
            data.suggestions.forEach(item => {
                const cardItem = document.createElement('div');
                cardItem.className = 'suggestion-item';
                
                cardItem.innerHTML = `
                    <div class="suggestion-bullet">💡</div>
                    <div class="suggestion-details">
                        <span class="suggestion-issue">${item.issue}</span>
                        <span class="suggestion-solution">${item.solution}</span>
                    </div>
                `;
                suggestionsContainer.appendChild(cardItem);
            });
        } else {
            suggestionsEmptyState.style.display = 'flex';
        }

        // Scroll results panel smoothly into view
        setTimeout(() => {
            resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 150);
    }

    /* ==========================================================================
       Audit Action Handlers (Copy, Export JSON, Export PDF)
       ========================================================================== */
    
    // 1. Copy Results Summary to Clipboard
    btnCopy.addEventListener('click', () => {
        if (!lastAnalysisReport) return;
        
        const r = lastAnalysisReport;
        const summary = `===========================================
C++ CODE COMPLEXITY AUDIT REPORT
===========================================
Time Complexity:       ${r.time_complexity} (${r.confidence_score}% Confidence)
Space Complexity:      ${r.space_complexity}
Cyclomatic Complexity: ${r.cyclomatic_complexity.overall_value} (${r.cyclomatic_complexity.risk_level})
Overall Quality Score: ${r.quality_scores.overall}/100

Health Metrics:
- Efficiency:      ${r.quality_scores.efficiency}%
- Readability:     ${r.quality_scores.readability}%
- Maintainability: ${r.quality_scores.maintainability}%
- Naming:          ${r.quality_scores.naming}%

General Stats:
- Functions:       ${r.stats.functions_count}
- Loops:           ${r.stats.loops_count}
- Variables:       ${r.stats.variables_count}
- Code Smells:     ${r.code_smells.length} detected

Generated via CodeComplexity.IO
===========================================`;
        
        navigator.clipboard.writeText(summary).then(() => {
            const originalText = btnCopy.innerHTML;
            btnCopy.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                <span>Copied!</span>
            `;
            setTimeout(() => {
                btnCopy.innerHTML = originalText;
            }, 2000);
        }).catch(err => {
            showError(`Failed to copy results: ${err}`);
        });
    });

    // 2. Export JSON Audit
    btnExportJson.addEventListener('click', () => {
        if (!lastAnalysisReport) return;
        
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(lastAnalysisReport, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", "code_complexity_audit_report.json");
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    });

    // 3. Download PDF Audit (using client-side html2pdf.js)
    btnExportPdf.addEventListener('click', () => {
        if (!lastAnalysisReport) return;
        
        // Hide the actions bar temporarily for PDF generation
        const actionsBar = document.querySelector('.actions-bar');
        actionsBar.style.display = 'none';

        // Select the results element
        const element = document.getElementById('results-panel');
        
        // Configure html2pdf parameters
        const opt = {
            margin:       0.3,
            filename:     'code_complexity_audit_report.pdf',
            image:        { type: 'jpeg', quality: 0.98 },
            html2canvas:  { 
                scale: 2, 
                useCORS: true, 
                backgroundColor: '#070a13',
                logging: false
            },
            jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
        };

        // Generate PDF
        html2pdf().set(opt).from(element).save().then(() => {
            // Restore actions bar visibility after generation completes
            actionsBar.style.display = 'flex';
        }).catch(err => {
            actionsBar.style.display = 'flex';
            showError(`PDF generation failed: ${err.message}`);
        });
    });

    /* ==========================================================================
       Helper Alert Functions
       ========================================================================== */
    function showError(message) {
        errorText.textContent = message;
        errorBanner.style.display = 'flex';
        setTimeout(() => {
            errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }
});
