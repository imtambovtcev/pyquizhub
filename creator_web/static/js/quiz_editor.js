/**
 * Shared Quiz Editor Component
 *
 * Used by both admin_web and creator_web interfaces.
 * Includes both JSON editor and Visual editor modes.
 *
 * Configuration options:
 * - apiEndpoints: { validate, create, generateToken }
 * - requireCreatorId: boolean - prompt for creator_id (admin) vs session (creator)
 * - showVisualEditor: boolean - show the visual editor tab
 * - showLoadTemplate: boolean - show load template button
 * - autoSaveDraft: boolean - auto-save to localStorage
 * - onQuizCreated: callback(quizId)
 */

class QuizEditor {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('QuizEditor: Container not found:', containerId);
            return;
        }

        this.options = {
            apiEndpoints: {
                validate: '/api/validate-quiz',
                create: '/api/quiz',
                generateToken: '/api/token/generate'
            },
            requireCreatorId: false,
            showVisualEditor: true,
            showLoadTemplate: true,
            autoSaveDraft: true,
            onQuizCreated: null,
            ...options
        };

        this.currentTab = this.options.showVisualEditor ? 'visual' : 'json';

        // Quiz data model
        this.quizData = {
            metadata: { title: '', description: '', version: '2.0' },
            variables: {},
            questions: [],
            transitions: {}
        };

        this.render();
        this.attachEventListeners();
        this.restoreDraft();
    }

    render() {
        const tabsHtml = this.options.showVisualEditor ? `
            <div class="editor-tabs">
                <button class="tab-btn ${this.currentTab === 'visual' ? 'active' : ''}" data-tab="visual">Visual Editor</button>
                <button class="tab-btn ${this.currentTab === 'json' ? 'active' : ''}" data-tab="json">JSON Editor</button>
            </div>
        ` : '';

        this.container.innerHTML = `
            <div class="quiz-editor-component">
                ${tabsHtml}

                <!-- Visual Editor Panel -->
                <div id="visual-editor" class="editor-panel ${this.currentTab === 'visual' ? 'active' : ''}">
                    ${this.renderVisualEditor()}
                </div>

                <!-- JSON Editor Panel -->
                <div id="json-editor" class="editor-panel ${this.currentTab === 'json' ? 'active' : ''}">
                    <div class="form-section">
                        <h3>Quiz JSON</h3>
                        <p class="help-text">Upload a JSON file or paste directly below.</p>
                        <div class="file-upload">
                            <input type="file" id="quiz-file" accept=".json" />
                            <label for="quiz-file" class="btn btn-secondary">Choose File</label>
                            <span id="file-name">No file selected</span>
                        </div>
                    </div>
                    <div class="form-section">
                        <textarea id="quiz-json" class="json-editor" rows="20" placeholder='Paste quiz JSON here...'></textarea>
                    </div>
                </div>

                <div class="form-actions">
                    <button class="btn btn-secondary validate-btn">Validate</button>
                    ${this.options.showLoadTemplate ? '<button class="btn btn-secondary load-template-btn">Load Template</button>' : ''}
                    <button class="btn btn-primary create-btn">Create Quiz</button>
                </div>

                <div id="validation-result" class="validation-result hidden"></div>
                <div id="create-result" class="create-result hidden"></div>
            </div>
        `;
    }

    renderVisualEditor() {
        return `
            <div class="visual-editor-container">
                <!-- Metadata Section -->
                <div class="editor-section">
                    <h3 class="section-header" data-toggle="metadata-content">
                        <span class="toggle-icon">▼</span> Quiz Metadata
                    </h3>
                    <div id="metadata-content" class="section-content">
                        <div class="form-row">
                            <div class="form-group">
                                <label for="quiz-title">Title *</label>
                                <input type="text" id="quiz-title" placeholder="My Quiz" value="${this.escapeHtml(this.quizData.metadata.title || '')}">
                            </div>
                            <div class="form-group">
                                <label for="quiz-version">Version</label>
                                <input type="text" id="quiz-version" placeholder="1.0" value="${this.escapeHtml(this.quizData.metadata.version || '2.0')}">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="quiz-description">Description</label>
                            <textarea id="quiz-description" rows="2" placeholder="A brief description of your quiz">${this.escapeHtml(this.quizData.metadata.description || '')}</textarea>
                        </div>
                    </div>
                </div>

                <!-- Variables Section -->
                <div class="editor-section">
                    <h3 class="section-header" data-toggle="variables-content">
                        <span class="toggle-icon">▼</span> Variables
                        <button class="btn btn-small add-variable-btn" onclick="event.stopPropagation()">+ Add Variable</button>
                    </h3>
                    <div id="variables-content" class="section-content">
                        <div id="variables-list" class="variables-list">
                            ${this.renderVariablesList()}
                        </div>
                    </div>
                </div>

                <!-- Questions Section -->
                <div class="editor-section">
                    <h3 class="section-header" data-toggle="questions-content">
                        <span class="toggle-icon">▼</span> Questions
                        <button class="btn btn-small add-question-btn" onclick="event.stopPropagation()">+ Add Question</button>
                    </h3>
                    <div id="questions-content" class="section-content">
                        <div id="questions-list" class="questions-list">
                            ${this.renderQuestionsList()}
                        </div>
                    </div>
                </div>

                <!-- Preview Section -->
                <div class="editor-section">
                    <h3 class="section-header" data-toggle="preview-content">
                        <span class="toggle-icon">▼</span> JSON Preview
                    </h3>
                    <div id="preview-content" class="section-content">
                        <pre id="json-preview" class="json-preview"></pre>
                    </div>
                </div>
            </div>
        `;
    }

    renderVariablesList() {
        const vars = Object.entries(this.quizData.variables);
        if (vars.length === 0) {
            return '<p class="empty-state">No variables defined. Click "Add Variable" to create one.</p>';
        }

        return vars.map(([name, config], index) => `
            <div class="variable-item" data-var-name="${this.escapeHtml(name)}">
                <div class="variable-header">
                    <span class="variable-name">${this.escapeHtml(name)}</span>
                    <span class="variable-type">${config.type || 'string'}</span>
                    <div class="variable-actions">
                        <button class="btn btn-small edit-variable-btn" data-var="${this.escapeHtml(name)}">Edit</button>
                        <button class="btn btn-small btn-danger delete-variable-btn" data-var="${this.escapeHtml(name)}">×</button>
                    </div>
                </div>
                <div class="variable-details">
                    ${config.default !== undefined ? `<span>Default: ${JSON.stringify(config.default)}</span>` : ''}
                    ${config.tags ? `<span>Tags: ${config.tags.join(', ')}</span>` : ''}
                </div>
            </div>
        `).join('');
    }

    renderQuestionsList() {
        if (this.quizData.questions.length === 0) {
            return '<p class="empty-state">No questions yet. Click "Add Question" to create one.</p>';
        }

        return this.quizData.questions.map((q, index) => `
            <div class="question-item" data-question-index="${index}">
                <div class="question-header">
                    <span class="question-number">Q${q.id || index + 1}</span>
                    <span class="question-type-badge">${q.data?.type || 'unknown'}</span>
                    <span class="question-text-preview">${this.escapeHtml(this.truncate(q.data?.text || '', 50))}</span>
                    <div class="question-actions">
                        <button class="btn btn-small move-up-btn" data-index="${index}" ${index === 0 ? 'disabled' : ''}>↑</button>
                        <button class="btn btn-small move-down-btn" data-index="${index}" ${index === this.quizData.questions.length - 1 ? 'disabled' : ''}>↓</button>
                        <button class="btn btn-small edit-question-btn" data-index="${index}">Edit</button>
                        <button class="btn btn-small btn-danger delete-question-btn" data-index="${index}">×</button>
                    </div>
                </div>
                ${this.renderQuestionPreview(q)}
            </div>
        `).join('');
    }

    renderQuestionPreview(question) {
        const data = question.data || {};
        let preview = '';

        if (data.type === 'multiple_choice' && data.options) {
            preview = `<div class="options-preview">${data.options.map(o =>
                `<span class="option-badge">${this.escapeHtml(o.label || o.value)}</span>`
            ).join('')}</div>`;
        } else if (data.type === 'final_message') {
            preview = '<span class="final-badge">Final Message</span>';
        }

        return preview;
    }

    attachEventListeners() {
        // Tab switching
        this.container.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Section toggles
        this.container.querySelectorAll('.section-header').forEach(header => {
            header.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn')) return;
                const contentId = header.dataset.toggle;
                const content = document.getElementById(contentId);
                const icon = header.querySelector('.toggle-icon');
                if (content) {
                    content.classList.toggle('collapsed');
                    icon.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
                }
            });
        });

        // File upload
        const fileInput = this.container.querySelector('#quiz-file');
        fileInput?.addEventListener('change', (e) => this.handleFileUpload(e));

        // JSON textarea
        const jsonTextarea = this.container.querySelector('#quiz-json');
        jsonTextarea?.addEventListener('input', () => this.handleJsonInput());

        // Metadata inputs
        this.container.querySelector('#quiz-title')?.addEventListener('input', (e) => {
            this.quizData.metadata.title = e.target.value;
            this.updatePreview();
        });
        this.container.querySelector('#quiz-description')?.addEventListener('input', (e) => {
            this.quizData.metadata.description = e.target.value;
            this.updatePreview();
        });
        this.container.querySelector('#quiz-version')?.addEventListener('input', (e) => {
            this.quizData.metadata.version = e.target.value;
            this.updatePreview();
        });

        // Add variable button
        this.container.querySelector('.add-variable-btn')?.addEventListener('click', () => this.showAddVariableModal());

        // Add question button
        this.container.querySelector('.add-question-btn')?.addEventListener('click', () => this.showAddQuestionModal());

        // Delegated events for dynamic elements
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('edit-variable-btn')) {
                this.showEditVariableModal(e.target.dataset.var);
            } else if (e.target.classList.contains('delete-variable-btn')) {
                this.deleteVariable(e.target.dataset.var);
            } else if (e.target.classList.contains('edit-question-btn')) {
                this.showEditQuestionModal(parseInt(e.target.dataset.index));
            } else if (e.target.classList.contains('delete-question-btn')) {
                this.deleteQuestion(parseInt(e.target.dataset.index));
            } else if (e.target.classList.contains('move-up-btn')) {
                this.moveQuestion(parseInt(e.target.dataset.index), -1);
            } else if (e.target.classList.contains('move-down-btn')) {
                this.moveQuestion(parseInt(e.target.dataset.index), 1);
            }
        });

        // Action buttons
        this.container.querySelector('.validate-btn')?.addEventListener('click', () => this.validateQuiz());
        this.container.querySelector('.load-template-btn')?.addEventListener('click', () => this.loadTemplate());
        this.container.querySelector('.create-btn')?.addEventListener('click', () => this.createQuiz());

        // Initial preview
        this.updatePreview();
    }

    switchTab(tab) {
        this.currentTab = tab;

        // Sync data between tabs
        if (tab === 'json') {
            // Sync visual to JSON
            const jsonTextarea = this.container.querySelector('#quiz-json');
            if (jsonTextarea) {
                jsonTextarea.value = JSON.stringify(this.quizData, null, 2);
            }
        } else if (tab === 'visual') {
            // Sync JSON to visual
            this.parseJsonToVisual();
        }

        // Update UI
        this.container.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        this.container.querySelector('#visual-editor')?.classList.toggle('active', tab === 'visual');
        this.container.querySelector('#json-editor')?.classList.toggle('active', tab === 'json');
    }

    parseJsonToVisual() {
        const jsonTextarea = this.container.querySelector('#quiz-json');
        if (!jsonTextarea?.value.trim()) return;

        try {
            const parsed = JSON.parse(jsonTextarea.value);
            this.quizData = {
                metadata: parsed.metadata || { title: '', description: '', version: '2.0' },
                variables: parsed.variables || {},
                questions: parsed.questions || [],
                transitions: parsed.transitions || {}
            };
            this.refreshVisualEditor();
        } catch (e) {
            // Invalid JSON, don't update visual
        }
    }

    refreshVisualEditor() {
        // Update metadata fields
        const titleInput = this.container.querySelector('#quiz-title');
        const descInput = this.container.querySelector('#quiz-description');
        const versionInput = this.container.querySelector('#quiz-version');

        if (titleInput) titleInput.value = this.quizData.metadata.title || '';
        if (descInput) descInput.value = this.quizData.metadata.description || '';
        if (versionInput) versionInput.value = this.quizData.metadata.version || '2.0';

        // Update lists
        const varsList = this.container.querySelector('#variables-list');
        if (varsList) varsList.innerHTML = this.renderVariablesList();

        const questionsList = this.container.querySelector('#questions-list');
        if (questionsList) questionsList.innerHTML = this.renderQuestionsList();

        this.updatePreview();
    }

    handleFileUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        const fileName = this.container.querySelector('#file-name');
        if (fileName) fileName.textContent = file.name;

        const reader = new FileReader();
        reader.onload = (e) => {
            const jsonTextarea = this.container.querySelector('#quiz-json');
            if (jsonTextarea) {
                jsonTextarea.value = e.target.result;
                this.parseJsonToVisual();
            }
        };
        reader.readAsText(file);
    }

    handleJsonInput() {
        if (this.options.autoSaveDraft) {
            const jsonTextarea = this.container.querySelector('#quiz-json');
            if (jsonTextarea) {
                localStorage.setItem('quiz-draft', jsonTextarea.value);
            }
        }
    }

    updatePreview() {
        const preview = this.container.querySelector('#json-preview');
        if (preview) {
            preview.textContent = JSON.stringify(this.buildQuizJson(), null, 2);
        }

        if (this.options.autoSaveDraft) {
            localStorage.setItem('quiz-draft-visual', JSON.stringify(this.quizData));
        }
    }

    buildQuizJson() {
        const quiz = {
            metadata: { ...this.quizData.metadata },
            variables: { ...this.quizData.variables },
            questions: [...this.quizData.questions],
            transitions: {}
        };

        // Auto-generate transitions if not set
        quiz.questions.forEach((q, i) => {
            const nextId = i < quiz.questions.length - 1 ? quiz.questions[i + 1].id : null;
            if (!quiz.transitions[q.id]) {
                quiz.transitions[q.id] = [{ expression: 'true', next_question_id: nextId }];
            }
        });

        return quiz;
    }

    restoreDraft() {
        if (!this.options.autoSaveDraft) return;

        const visualDraft = localStorage.getItem('quiz-draft-visual');
        const jsonDraft = localStorage.getItem('quiz-draft');

        if (visualDraft || jsonDraft) {
            if (confirm('Restore previous draft?')) {
                if (visualDraft) {
                    try {
                        this.quizData = JSON.parse(visualDraft);
                        this.refreshVisualEditor();
                    } catch (e) {}
                }
                if (jsonDraft) {
                    const jsonTextarea = this.container.querySelector('#quiz-json');
                    if (jsonTextarea) jsonTextarea.value = jsonDraft;
                }
            }
        }
    }

    // Variable Management
    showAddVariableModal() {
        this.showModal('Add Variable', `
            <div class="form-group">
                <label>Variable Name *</label>
                <input type="text" id="modal-var-name" placeholder="score">
            </div>
            <div class="form-group">
                <label>Type *</label>
                <select id="modal-var-type">
                    <option value="integer">Integer</option>
                    <option value="string">String</option>
                    <option value="float">Float</option>
                    <option value="boolean">Boolean</option>
                    <option value="array">Array</option>
                </select>
            </div>
            <div class="form-group">
                <label>Default Value</label>
                <input type="text" id="modal-var-default" placeholder="0">
            </div>
            <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" id="modal-var-tags" placeholder="score, public">
            </div>
        `, () => {
            const name = document.getElementById('modal-var-name').value.trim();
            const type = document.getElementById('modal-var-type').value;
            const defaultVal = document.getElementById('modal-var-default').value;
            const tags = document.getElementById('modal-var-tags').value.split(',').map(t => t.trim()).filter(t => t);

            if (!name) {
                alert('Variable name is required');
                return false;
            }

            let parsedDefault;
            if (defaultVal) {
                if (type === 'integer') parsedDefault = parseInt(defaultVal) || 0;
                else if (type === 'float') parsedDefault = parseFloat(defaultVal) || 0;
                else if (type === 'boolean') parsedDefault = defaultVal.toLowerCase() === 'true';
                else if (type === 'array') {
                    try { parsedDefault = JSON.parse(defaultVal); } catch { parsedDefault = []; }
                } else parsedDefault = defaultVal;
            }

            this.quizData.variables[name] = {
                type,
                mutable_by: ['engine'],
                ...(tags.length > 0 ? { tags } : {}),
                ...(parsedDefault !== undefined ? { default: parsedDefault } : {})
            };

            this.refreshVariablesList();
            this.updatePreview();
            return true;
        });
    }

    showEditVariableModal(varName) {
        const config = this.quizData.variables[varName];
        if (!config) return;

        this.showModal('Edit Variable', `
            <div class="form-group">
                <label>Variable Name</label>
                <input type="text" id="modal-var-name" value="${this.escapeHtml(varName)}" disabled>
            </div>
            <div class="form-group">
                <label>Type</label>
                <select id="modal-var-type">
                    <option value="integer" ${config.type === 'integer' ? 'selected' : ''}>Integer</option>
                    <option value="string" ${config.type === 'string' ? 'selected' : ''}>String</option>
                    <option value="float" ${config.type === 'float' ? 'selected' : ''}>Float</option>
                    <option value="boolean" ${config.type === 'boolean' ? 'selected' : ''}>Boolean</option>
                    <option value="array" ${config.type === 'array' ? 'selected' : ''}>Array</option>
                </select>
            </div>
            <div class="form-group">
                <label>Default Value</label>
                <input type="text" id="modal-var-default" value="${config.default !== undefined ? JSON.stringify(config.default) : ''}">
            </div>
            <div class="form-group">
                <label>Tags (comma-separated)</label>
                <input type="text" id="modal-var-tags" value="${(config.tags || []).join(', ')}">
            </div>
        `, () => {
            const type = document.getElementById('modal-var-type').value;
            const defaultVal = document.getElementById('modal-var-default').value;
            const tags = document.getElementById('modal-var-tags').value.split(',').map(t => t.trim()).filter(t => t);

            let parsedDefault;
            if (defaultVal) {
                try { parsedDefault = JSON.parse(defaultVal); } catch { parsedDefault = defaultVal; }
            }

            this.quizData.variables[varName] = {
                type,
                mutable_by: ['engine'],
                ...(tags.length > 0 ? { tags } : {}),
                ...(parsedDefault !== undefined ? { default: parsedDefault } : {})
            };

            this.refreshVariablesList();
            this.updatePreview();
            return true;
        });
    }

    deleteVariable(varName) {
        if (confirm(`Delete variable "${varName}"?`)) {
            delete this.quizData.variables[varName];
            this.refreshVariablesList();
            this.updatePreview();
        }
    }

    refreshVariablesList() {
        const list = this.container.querySelector('#variables-list');
        if (list) list.innerHTML = this.renderVariablesList();
    }

    // Question Management
    showAddQuestionModal() {
        const nextId = this.quizData.questions.length > 0
            ? Math.max(...this.quizData.questions.map(q => q.id || 0)) + 1
            : 1;

        this.showModal('Add Question', this.renderQuestionForm(nextId), () => {
            const question = this.parseQuestionForm();
            if (!question) return false;

            this.quizData.questions.push(question);
            this.refreshQuestionsList();
            this.updatePreview();
            return true;
        });
    }

    showEditQuestionModal(index) {
        const question = this.quizData.questions[index];
        if (!question) return;

        this.showModal('Edit Question', this.renderQuestionForm(question.id, question), () => {
            const updated = this.parseQuestionForm();
            if (!updated) return false;

            this.quizData.questions[index] = updated;
            this.refreshQuestionsList();
            this.updatePreview();
            return true;
        });
    }

    renderQuestionForm(id, question = null) {
        const data = question?.data || {};
        const type = data.type || 'multiple_choice';
        const options = data.options || [];
        const scoreUpdates = question?.score_updates || [];

        // Render options list
        let optionsHtml = '';
        if (options.length > 0) {
            optionsHtml = options.map((opt, i) => `
                <div class="option-row" data-index="${i}">
                    <input type="text" class="option-label" placeholder="Label" value="${this.escapeHtml(opt.label || '')}">
                    <input type="text" class="option-value" placeholder="Value" value="${this.escapeHtml(opt.value || '')}">
                    <button type="button" class="btn btn-small btn-danger remove-option-btn">×</button>
                </div>
            `).join('');
        }

        // Render score updates list
        let scoreUpdatesHtml = '';
        if (scoreUpdates.length > 0) {
            scoreUpdatesHtml = scoreUpdates.map((su, i) => {
                const updates = Object.entries(su.update || {});
                return `
                    <div class="score-update-row" data-index="${i}">
                        <div class="score-update-condition">
                            <label>When:</label>
                            <input type="text" class="score-condition" placeholder="answer == 'yes'" value="${this.escapeHtml(su.condition || '')}">
                        </div>
                        <div class="score-update-actions">
                            ${updates.map(([varName, expr]) => `
                                <div class="score-action-row">
                                    <select class="score-var-select">
                                        ${Object.keys(this.quizData.variables).map(v =>
                                            `<option value="${v}" ${v === varName ? 'selected' : ''}>${v}</option>`
                                        ).join('')}
                                    </select>
                                    <span>=</span>
                                    <input type="text" class="score-expr" placeholder="score + 1" value="${this.escapeHtml(expr || '')}">
                                </div>
                            `).join('')}
                        </div>
                        <button type="button" class="btn btn-small btn-danger remove-score-btn">×</button>
                    </div>
                `;
            }).join('');
        }

        return `
            <div class="form-group">
                <label>Question ID</label>
                <input type="number" id="modal-q-id" value="${id}" min="1">
            </div>
            <div class="form-group">
                <label>Question Type *</label>
                <select id="modal-q-type" onchange="window._quizEditorTypeChange && window._quizEditorTypeChange()">
                    <option value="multiple_choice" ${type === 'multiple_choice' ? 'selected' : ''}>Multiple Choice</option>
                    <option value="integer" ${type === 'integer' ? 'selected' : ''}>Integer Input</option>
                    <option value="float" ${type === 'float' ? 'selected' : ''}>Float Input</option>
                    <option value="text" ${type === 'text' ? 'selected' : ''}>Text Input</option>
                    <option value="multiple_select" ${type === 'multiple_select' ? 'selected' : ''}>Multiple Select</option>
                    <option value="final_message" ${type === 'final_message' ? 'selected' : ''}>Final Message</option>
                </select>
            </div>
            <div class="form-group">
                <label>${type === 'final_message' ? 'Message Text *' : 'Question Text *'}</label>
                <textarea id="modal-q-text" rows="3" placeholder="${type === 'final_message' ? 'Your score: {variables.score}' : 'Enter your question...'}">${this.escapeHtml(data.text || '')}</textarea>
                ${type === 'final_message' ? '<p class="help-text">Use {variables.name} to show variable values</p>' : ''}
            </div>
            <div id="options-section" class="form-group" style="${['multiple_choice', 'multiple_select'].includes(type) ? '' : 'display:none'}">
                <label>Answer Options</label>
                <div id="options-list" class="options-list">
                    ${optionsHtml}
                </div>
                <button type="button" class="btn btn-small add-option-btn">+ Add Option</button>
            </div>
            <div class="form-group">
                <label>Image URL (optional)</label>
                <input type="text" id="modal-q-image" value="${this.escapeHtml(data.image_url || '')}" placeholder="https://example.com/image.png">
            </div>
            <div id="score-section" class="form-group" style="${type === 'final_message' ? 'display:none' : ''}">
                <label>Score Updates (when answer is submitted)</label>
                <div id="score-updates-list" class="score-updates-list">
                    ${scoreUpdatesHtml}
                </div>
                <button type="button" class="btn btn-small add-score-btn">+ Add Score Rule</button>
            </div>
        `;
    }

    parseQuestionForm() {
        const id = parseInt(document.getElementById('modal-q-id').value);
        const type = document.getElementById('modal-q-type').value;
        const text = document.getElementById('modal-q-text').value.trim();
        const imageUrl = document.getElementById('modal-q-image').value.trim();

        if (!text) {
            alert('Question text is required');
            return null;
        }

        const question = {
            id,
            data: { type, text }
        };

        if (imageUrl) {
            question.data.image_url = imageUrl;
        }

        // Parse options from visual inputs
        if (['multiple_choice', 'multiple_select'].includes(type)) {
            const optionRows = document.querySelectorAll('#options-list .option-row');
            const options = [];
            optionRows.forEach(row => {
                const label = row.querySelector('.option-label').value.trim();
                const value = row.querySelector('.option-value').value.trim();
                if (label || value) {
                    options.push({ label: label || value, value: value || label });
                }
            });
            if (options.length > 0) {
                question.data.options = options;
            }
        }

        // Parse score updates from visual inputs
        const scoreRows = document.querySelectorAll('#score-updates-list .score-update-row');
        if (scoreRows.length > 0) {
            const scoreUpdates = [];
            scoreRows.forEach(row => {
                const condition = row.querySelector('.score-condition').value.trim();
                const actionRows = row.querySelectorAll('.score-action-row');
                const update = {};
                actionRows.forEach(actionRow => {
                    const varName = actionRow.querySelector('.score-var-select').value;
                    const expr = actionRow.querySelector('.score-expr').value.trim();
                    if (varName && expr) {
                        update[varName] = expr;
                    }
                });
                if (condition && Object.keys(update).length > 0) {
                    scoreUpdates.push({ condition, update });
                }
            });
            if (scoreUpdates.length > 0) {
                question.score_updates = scoreUpdates;
            }
        }

        return question;
    }

    deleteQuestion(index) {
        const q = this.quizData.questions[index];
        if (confirm(`Delete question ${q.id}?`)) {
            this.quizData.questions.splice(index, 1);
            this.refreshQuestionsList();
            this.updatePreview();
        }
    }

    moveQuestion(index, direction) {
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= this.quizData.questions.length) return;

        const temp = this.quizData.questions[index];
        this.quizData.questions[index] = this.quizData.questions[newIndex];
        this.quizData.questions[newIndex] = temp;

        this.refreshQuestionsList();
        this.updatePreview();
    }

    refreshQuestionsList() {
        const list = this.container.querySelector('#questions-list');
        if (list) list.innerHTML = this.renderQuestionsList();
    }

    // Modal
    showModal(title, content, onSave) {
        const self = this;

        // Set up type change handler
        window._quizEditorTypeChange = () => {
            const type = document.getElementById('modal-q-type')?.value;
            const optionsSection = document.getElementById('options-section');
            const scoreSection = document.getElementById('score-section');
            if (optionsSection) {
                optionsSection.style.display = ['multiple_choice', 'multiple_select'].includes(type) ? '' : 'none';
            }
            if (scoreSection) {
                scoreSection.style.display = type === 'final_message' ? 'none' : '';
            }
        };

        const modal = document.createElement('div');
        modal.className = 'editor-modal-overlay';
        modal.innerHTML = `
            <div class="editor-modal">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">×</button>
                </div>
                <div class="modal-body">${content}</div>
                <div class="modal-footer">
                    <button class="btn btn-secondary modal-cancel">Cancel</button>
                    <button class="btn btn-primary modal-save">Save</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const close = () => {
            modal.remove();
            window._quizEditorTypeChange = null;
        };

        // Add option button
        modal.querySelector('.add-option-btn')?.addEventListener('click', () => {
            const list = modal.querySelector('#options-list');
            const index = list.querySelectorAll('.option-row').length;
            const row = document.createElement('div');
            row.className = 'option-row';
            row.dataset.index = index;
            row.innerHTML = `
                <input type="text" class="option-label" placeholder="Label (e.g., Yes)">
                <input type="text" class="option-value" placeholder="Value (e.g., yes)">
                <button type="button" class="btn btn-small btn-danger remove-option-btn">×</button>
            `;
            list.appendChild(row);
        });

        // Remove option button (delegated)
        modal.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-option-btn')) {
                e.target.closest('.option-row').remove();
            }
            if (e.target.classList.contains('remove-score-btn')) {
                e.target.closest('.score-update-row').remove();
            }
        });

        // Add score rule button
        modal.querySelector('.add-score-btn')?.addEventListener('click', () => {
            const list = modal.querySelector('#score-updates-list');
            const index = list.querySelectorAll('.score-update-row').length;
            const varOptions = Object.keys(self.quizData.variables).map(v =>
                `<option value="${v}">${v}</option>`
            ).join('') || '<option value="">No variables defined</option>';

            const row = document.createElement('div');
            row.className = 'score-update-row';
            row.dataset.index = index;
            row.innerHTML = `
                <div class="score-update-condition">
                    <label>When:</label>
                    <input type="text" class="score-condition" placeholder="answer == 'yes'">
                </div>
                <div class="score-update-actions">
                    <div class="score-action-row">
                        <select class="score-var-select">${varOptions}</select>
                        <span>=</span>
                        <input type="text" class="score-expr" placeholder="score + 1">
                    </div>
                </div>
                <button type="button" class="btn btn-small btn-danger remove-score-btn">×</button>
            `;
            list.appendChild(row);
        });

        modal.querySelector('.modal-close').addEventListener('click', close);
        modal.querySelector('.modal-cancel').addEventListener('click', close);
        modal.querySelector('.modal-save').addEventListener('click', () => {
            if (onSave()) close();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) close();
        });
    }

    // Validation & Creation
    async validateQuiz() {
        const quizData = this.currentTab === 'visual' ? this.buildQuizJson() : this.getJsonFromTextarea();
        if (!quizData) return;

        try {
            const response = await fetch(this.options.apiEndpoints.validate, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(quizData)
            });

            const result = await response.json();

            if (result.errors?.length > 0) {
                this.showResult('validation-result', 'error',
                    '<strong>Validation Errors:</strong><ul>' +
                    result.errors.map(e => `<li>${this.escapeHtml(e)}</li>`).join('') + '</ul>');
            } else {
                let msg = '<strong>✓ Validation Passed!</strong>';
                if (result.warnings?.length > 0) {
                    msg += '<br><strong>Warnings:</strong><ul>' +
                        result.warnings.map(w => `<li>${this.escapeHtml(w)}</li>`).join('') + '</ul>';
                }
                this.showResult('validation-result', 'success', msg);
            }
        } catch (e) {
            this.showResult('validation-result', 'error', `Error: ${e.message}`);
        }
    }

    async createQuiz() {
        const quizData = this.currentTab === 'visual' ? this.buildQuizJson() : this.getJsonFromTextarea();
        if (!quizData) return;

        const payload = { quiz: quizData };

        if (this.options.requireCreatorId) {
            const creatorId = prompt('Enter creator ID:', 'admin');
            if (!creatorId) return;
            payload.creator_id = creatorId;
        }

        try {
            const response = await fetch(this.options.apiEndpoints.create, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok) {
                let msg = `<strong>Quiz Created!</strong><br>Quiz ID: <code>${result.quiz_id}</code>`;

                if (confirm('Quiz created! Generate a token now?')) {
                    const tokenType = confirm('Permanent token? (Cancel for single-use)') ? 'permanent' : 'single-use';
                    const tokenRes = await fetch(this.options.apiEndpoints.generateToken, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ quiz_id: result.quiz_id, type: tokenType })
                    });
                    const tokenData = await tokenRes.json();
                    if (tokenRes.ok) {
                        msg += `<br>Token: <code>${tokenData.token}</code>`;
                        prompt('Copy token:', tokenData.token);
                    }
                }

                this.showResult('create-result', 'success', msg);
                this.clearDraft();

                if (this.options.onQuizCreated) {
                    this.options.onQuizCreated(result.quiz_id);
                }
            } else {
                const errorMsg = typeof result.detail === 'object'
                    ? JSON.stringify(result.detail, null, 2)
                    : result.detail || result.error || 'Unknown error';
                this.showResult('create-result', 'error', `<strong>Creation Failed:</strong><br>${this.escapeHtml(errorMsg)}`);
            }
        } catch (e) {
            this.showResult('create-result', 'error', `Error: ${e.message}`);
        }
    }

    getJsonFromTextarea() {
        const textarea = this.container.querySelector('#quiz-json');
        if (!textarea?.value.trim()) {
            this.showResult('validation-result', 'error', 'Please enter quiz JSON');
            return null;
        }
        try {
            return JSON.parse(textarea.value);
        } catch (e) {
            this.showResult('validation-result', 'error', `Invalid JSON: ${e.message}`);
            return null;
        }
    }

    loadTemplate() {
        this.quizData = {
            metadata: { title: 'My Quiz', description: 'A sample quiz', version: '2.0' },
            variables: {
                score: { type: 'integer', mutable_by: ['engine'], tags: ['score'], default: 0 }
            },
            questions: [
                {
                    id: 1,
                    data: {
                        type: 'multiple_choice',
                        text: 'What is 2 + 2?',
                        options: [
                            { label: '3', value: '3' },
                            { label: '4', value: '4' },
                            { label: '5', value: '5' }
                        ]
                    },
                    score_updates: [{ condition: "answer == '4'", update: { score: 'score + 10' } }]
                },
                {
                    id: 2,
                    data: { type: 'final_message', text: 'Your score: {variables.score}' }
                }
            ],
            transitions: {}
        };

        this.refreshVisualEditor();

        // Also update JSON tab
        const jsonTextarea = this.container.querySelector('#quiz-json');
        if (jsonTextarea) {
            jsonTextarea.value = JSON.stringify(this.buildQuizJson(), null, 2);
        }

        this.showResult('create-result', 'success', 'Template loaded!');
    }

    clearDraft() {
        localStorage.removeItem('quiz-draft');
        localStorage.removeItem('quiz-draft-visual');
        this.quizData = {
            metadata: { title: '', description: '', version: '2.0' },
            variables: {},
            questions: [],
            transitions: {}
        };
        this.refreshVisualEditor();
        const jsonTextarea = this.container.querySelector('#quiz-json');
        if (jsonTextarea) jsonTextarea.value = '';
    }

    showResult(elementId, type, message) {
        const element = this.container.querySelector(`#${elementId}`);
        if (element) {
            element.className = `${elementId.includes('validation') ? 'validation-result' : 'create-result'} ${type}`;
            element.innerHTML = message;
            element.classList.remove('hidden');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncate(str, len) {
        return str.length > len ? str.substring(0, len) + '...' : str;
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = QuizEditor;
}
