import { v4 as uuidv4 } from 'https://cdn.jsdelivr.net/npm/uuid@8.3.2/dist/esm-browser/index.js';

const API_BASE_URL = `http://${window.location.hostname}:8000`;

class QuizApp {
    constructor() {
        this.startScreen = document.getElementById('start-screen');
        this.quizScreen = document.getElementById('quiz-screen');
        this.startForm = document.getElementById('start-form');
        this.quizForm = document.getElementById('quiz-form');
        this.errorMessage = document.getElementById('error-message');
        this.quizError = document.getElementById('quiz-error');

        this.currentQuiz = null;
        this.userId = uuidv4();  // Use uuidv4 to generate a UUID

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.startForm.addEventListener('submit', (e) => this.handleStartQuiz(e));
        this.quizForm.addEventListener('submit', (e) => this.handleSubmitAnswer(e));
    }

    async handleStartQuiz(event) {
        event.preventDefault();
        const token = document.getElementById('token').value;

        try {
            const response = await fetch(`${API_BASE_URL}/quiz/start_quiz`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({
                    token,
                    user_id: this.userId  // Changed from userId to user_id to match API
                })
            });

            const data = await response.json();

            if (!response.ok) throw new Error(data.detail || 'Failed to start quiz');

            this.currentQuiz = data;
            this.showQuiz(data.question);
        } catch (error) {
            this.showError(error.message);
        }
    }

    async handleSubmitAnswer(event) {
        event.preventDefault();
        if (!this.currentQuiz) return;

        try {
            const answer = this.getAnswer();
            console.log("Submitting answer:", answer);
            const response = await fetch(`${API_BASE_URL}/quiz/submit_answer/${this.currentQuiz.quiz_id}`, {  // Changed from quizId to quiz_id
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                body: JSON.stringify({
                    quiz_id: this.currentQuiz.quiz_id,
                    session_id: this.currentQuiz.session_id,
                    user_id: this.userId,
                    answer: { answer }  // Ensure answer is sent as a dictionary
                })
            });

            const data = await response.json();
            console.log("Response from API:", data);

            if (!response.ok) throw new Error(data.detail || 'Failed to submit answer');

            if (data.question.id === null) {
                this.showResults(data);
            } else {
                this.showQuiz(data.question);
            }
        } catch (error) {
            console.error("Error submitting answer:", error);
            this.showQuizError(error.message);
        }
    }

    getAnswer() {
        const questionType = this.currentQuiz.question.data.type;
        switch (questionType) {
            case 'multiple_choice':
                return this.getSelectedRadioValue();
            case 'multiple_select':
                return this.getSelectedCheckboxValues();
            case 'text':
            case 'number':
            case 'integer':
            case 'float':
                return document.getElementById('answer-input').value;
            default:
                throw new Error(`Unsupported question type: ${questionType}`);
        }
    }

    getSelectedRadioValue() {
        const selected = document.querySelector('input[name="answer"]:checked');
        return selected ? selected.value : null;
    }

    getSelectedCheckboxValues() {
        return Array.from(document.querySelectorAll('input[name="answer"]:checked'))
            .map(cb => cb.value);
    }

    showQuiz(question) {
        if (question.id === null) {
            this.showResults({ score: "Quiz completed!" });
            return;
        }

        this.startScreen.style.display = 'none';
        this.quizScreen.style.display = 'block';

        document.getElementById('question-text').textContent = question.data.text;
        const choicesDiv = document.getElementById('choices');
        choicesDiv.innerHTML = this.generateChoicesHtml(question);
    }

    generateChoicesHtml(question) {
        console.log(question);
        switch (question.data.type) {
            case 'multiple_choice':
                return this.generateRadioChoices(question.data.options);
            case 'multiple_select':
                return this.generateCheckboxChoices(question.data.options);
            case 'number':
                return this.generateInputField(question.data.type);
            case 'integer':
                return this.generateInputField('number');
            case 'float':
                return this.generateInputField('number', 'step="any"');
            case 'text':
                return this.generateInputField('text');
            case 'final_message':
                return `<p>${question.data.text}</p>`;
            default:
                return `<p>Unsupported question type: ${question.data.type}</p>`;
        }
    }

    generateRadioChoices(choices) {
        return choices.map((choice, index) => `
            <label class="choice">
                <input type="radio" name="answer" value="${choice.value}" required>
                ${choice.label}
            </label>
        `).join('');
    }

    generateCheckboxChoices(choices) {
        return choices.map((choice, index) => `
            <label class="choice">
                <input type="checkbox" name="answer" value="${choice.value}">
                ${choice.label}
            </label>
        `).join('');
    }

    generateInputField(type, additionalAttributes = '') {
        return `
            <input type="${type}" id="answer-input" name="answer" required ${additionalAttributes}>
        `;
    }

    showResults(data) {
        this.quizScreen.innerHTML = `
            <div class="success">
                <h2>Quiz Completed!</h2>
                <p>Your score: ${data.score}</p>
            </div>
        `;
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
    }

    showQuizError(message) {
        this.quizError.textContent = message;
        this.quizError.style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new QuizApp();
});
