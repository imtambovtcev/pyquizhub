# Use Case: Complex Quiz with Branching Logic

## Overview
This use case demonstrates the creation and execution of a complex quiz with multiple score tracking, conditional logic, and branching pathways using PyQuizHub.

## Use Case Details

**Use Case ID:** UC-001  
**Use Case Name:** Complex Quiz with Conditional Branching  
**Actor:** Quiz Administrator, Quiz Participant  
**Goal:** Create and complete a quiz that adapts based on user responses  
**Preconditions:** 
- PyQuizHub system is deployed and running
- Admin has valid authentication token
- PostgreSQL database is initialized

## Quiz Specification

### Metadata
- **Title:** Complex Quiz
- **Description:** A quiz with multiple scores, branching logic, and conditions
- **Author:** Advanced Author
- **Version:** 2.0

### Score Tracking
The quiz tracks three separate scores:
- `fruits`: General fruit preference counter (starts at 0)
- `apples`: Apple-specific preference score (starts at 0)
- `pears`: Pear-specific preference score (starts at 0)

### Questions

#### Question 1: Apple Preference
- **ID:** 1
- **Type:** Multiple Choice
- **Text:** "Do you like apples?"
- **Options:**
  - Yes
  - No

**Score Update Logic:**
- If answer is "yes":
  - `fruits = fruits + 1`
  - `apples = apples + 2`
- If answer is "no":
  - `apples = apples - 1`

**Transition Logic:**
- If `fruits >= 1` → Proceed to Question 2
- Otherwise (`true` fallback) → Loop back to Question 1

#### Question 2: Pear Preference
- **ID:** 2
- **Type:** Multiple Choice
- **Text:** "Do you like pears?"
- **Options:**
  - Yes
  - No

**Score Update Logic:**
- If answer is "yes":
  - `fruits = fruits + 1`
  - `pears = pears + 2`
- If answer is "no":
  - No score updates

**Transition Logic:**
- Always (`true`) → End quiz (null next question)

## Scenario Flow

### Scenario 1: Direct Path (Positive Fruit Lover)

**Participant:** User "test_user_1"

#### Step 1: Quiz Creation
**Actor:** Administrator

1. Administrator prepares quiz JSON file with metadata, questions, scores, and transitions
2. Administrator sends POST request to `/admin/create_quiz` endpoint
3. System validates quiz structure:
   - Checks for required metadata fields
   - Validates question IDs are unique
   - Verifies score update expressions are syntactically correct
   - Ensures transition conditions reference valid question IDs
4. System generates unique quiz ID: `COMPLEXQUIC4J3DN`
5. System stores quiz in database
6. System returns quiz ID and title

**Result:** Quiz successfully created and ready for use

#### Step 2: Token Generation
**Actor:** Administrator

1. Administrator requests permanent access token for quiz `COMPLEXQUIC4J3DN`
2. System generates unique token: `AVOKNQW61EIYHZD7`
3. System associates token with quiz and sets type as "permanent"
4. System stores token in database
5. System returns token to administrator

**Result:** Token `AVOKNQW61EIYHZD7` can be distributed to participants

#### Step 3: Quiz Start
**Actor:** Participant (test_user_1)

1. Participant provides quiz token and user ID to `/quiz/start_quiz` endpoint
2. System validates token:
   - Checks if token exists
   - Verifies token is associated with valid quiz
   - Confirms token hasn't been consumed (for single-use tokens)
3. System creates new quiz session:
   - Generates session ID: `61996ad5-e214-47dc-975a-d3b2e944ee55`
   - Initializes scores: `{fruits: 0, apples: 0, pears: 0}`
   - Sets current question to first question (ID: 1)
4. System returns:
   - Quiz metadata (title, quiz_id, session_id)
   - Current question data (Question 1 about apples)

**Result:** Quiz session started, participant sees Question 1

#### Step 4: Answer Question 1 - "Yes"
**Actor:** Participant (test_user_1)

1. Participant submits answer "yes" with session ID
2. System retrieves session state:
   - Current scores: `{fruits: 0, apples: 0, pears: 0}`
   - Current question: 1
3. System processes answer:
   - Evaluates condition `answer == 'yes'` → True
   - Executes score updates:
     - `fruits = 0 + 1 = 1`
     - `apples = 0 + 2 = 2`
   - Updates session with new scores
4. System determines next question:
   - Evaluates transition `fruits >= 1` → True (1 >= 1)
   - Next question ID: 2
5. System retrieves Question 2 data
6. System returns Question 2 about pears

**Current State:**
- Scores: `{fruits: 1, apples: 2, pears: 0}`
- Current Question: 2

**Result:** Participant advanced to Question 2 based on conditional logic

#### Step 5: Answer Question 2 - "Yes"
**Actor:** Participant (test_user_1)

1. Participant submits answer "yes"
2. System retrieves session state:
   - Current scores: `{fruits: 1, apples: 2, pears: 0}`
   - Current question: 2
3. System processes answer:
   - Evaluates condition `answer == 'yes'` → True
   - Executes score updates:
     - `fruits = 1 + 1 = 2`
     - `pears = 0 + 2 = 2`
   - Updates session with new scores
4. System determines next question:
   - Evaluates transition `true` → Always true
   - Next question ID: null (end of quiz)
5. System marks session as completed
6. System returns null question (quiz complete)

**Final State:**
- Scores: `{fruits: 2, apples: 2, pears: 2}`
- Quiz Status: Completed

**Result:** Quiz completed successfully with all fruit preferences recorded

---

### Scenario 2: Looping Path (Initial Apple Rejection)

**Participant:** User "test_user_2"

#### Step 1: Quiz Start
**Actor:** Participant (test_user_2)

1. Participant starts quiz with same token `AVOKNQW61EIYHZD7`
2. System creates independent session: `aefb47e9-8b4d-40fa-994c-cd219ff688f4`
3. System initializes scores: `{fruits: 0, apples: 0, pears: 0}`
4. System presents Question 1

**Result:** New session started independently from test_user_1

#### Step 2: Answer Question 1 - "No" (First Attempt)
**Actor:** Participant (test_user_2)

1. Participant submits answer "no"
2. System processes answer:
   - Evaluates condition `answer == 'no'` → True
   - Executes score update:
     - `apples = 0 - 1 = -1`
   - Other scores unchanged
3. System determines next question:
   - Evaluates first transition `fruits >= 1` → False (0 >= 1)
   - Evaluates fallback transition `true` → True
   - Next question ID: 1 (loop back)
4. System returns Question 1 again

**Current State:**
- Scores: `{fruits: 0, apples: -1, pears: 0}`
- Current Question: 1 (looped back)

**Result:** Participant loops back to Question 1 due to conditional branching

#### Step 3: Answer Question 1 - "Yes" (Second Attempt)
**Actor:** Participant (test_user_2)

1. Participant submits answer "yes"
2. System processes answer:
   - Evaluates condition `answer == 'yes'` → True
   - Executes score updates:
     - `fruits = 0 + 1 = 1`
     - `apples = -1 + 2 = 1`
3. System determines next question:
   - Evaluates transition `fruits >= 1` → True (1 >= 1)
   - Next question ID: 2
4. System presents Question 2

**Current State:**
- Scores: `{fruits: 1, apples: 1, pears: 0}`
- Current Question: 2

**Result:** Participant successfully progressed to Question 2 after changing answer

#### Step 4: Answer Question 2 - "No"
**Actor:** Participant (test_user_2)

1. Participant submits answer "no"
2. System processes answer:
   - Evaluates condition `answer == 'yes'` → False
   - No score updates match (no condition for "no" answer)
   - Scores remain unchanged
3. System determines next question:
   - Evaluates transition `true` → Always true
   - Next question ID: null (end of quiz)
4. System marks session as completed

**Final State:**
- Scores: `{fruits: 1, apples: 1, pears: 0}`
- Quiz Status: Completed

**Result:** Quiz completed with different score profile than Scenario 1

## Key Features Demonstrated

### 1. Multi-Score Tracking
- Three independent score variables tracked simultaneously
- Scores can be positive or negative
- Score updates based on conditional logic

### 2. Conditional Score Updates
- Different score modifications based on answer values
- Expression evaluation: `answer == 'yes'`, `answer == 'no'`
- Arithmetic operations: `fruits + 1`, `apples + 2`, `apples - 1`

### 3. Dynamic Branching Logic
- Conditional transitions based on score state
- Looping capability (returning to same question)
- Progressive transitions (moving to next question)
- Fallback transitions (default path when conditions fail)

### 4. Session Independence
- Multiple users can take same quiz simultaneously
- Each session maintains independent state
- Score calculations isolated per session

### 5. Token-Based Access Control
- Permanent tokens allow multiple uses
- Tokens can be distributed to multiple users
- Each user creates their own session

## Technical Implementation Details

### API Endpoints Used

1. **POST /admin/create_quiz**
   - Request: Quiz JSON + creator_id
   - Response: quiz_id, title
   - Authentication: Admin token required

2. **POST /admin/generate_token**
   - Request: quiz_id, type (permanent/single-use)
   - Response: token
   - Authentication: Admin token required

3. **POST /quiz/start_quiz**
   - Request: token, user_id
   - Response: quiz_id, session_id, title, first question
   - Authentication: User token required

4. **POST /quiz/submit_answer/{quiz_id}**
   - Request: user_id, session_id, answer
   - Response: next question or null (if complete)
   - Authentication: User token required

### Data Flow

```
Quiz Creation → Token Generation → Quiz Start → Answer Loop → Completion
     ↓                ↓                ↓              ↓            ↓
  Storage          Storage          Session       Session      Session
  (Quiz)          (Token)          Created       Updated      Completed
```

### Expression Evaluation

The system evaluates two types of expressions:

1. **Condition Expressions** (Boolean)
   - Used in score_updates and transitions
   - Examples: `answer == 'yes'`, `fruits >= 1`, `true`
   - Context: answer value, current scores

2. **Update Expressions** (Arithmetic)
   - Used in score modifications
   - Examples: `fruits + 1`, `apples + 2`, `apples - 1`
   - Context: current score values

## Business Value

### For Quiz Creators
- Create adaptive quizzes that respond to user input
- Track multiple metrics simultaneously
- Implement complex business logic without programming
- Reuse quiz structure for different user groups

### For Quiz Participants
- Personalized quiz experience
- Immediate feedback through branching
- Opportunity to revisit questions (if designed)
- Clear progress through quiz flow

### For Organizations
- Scalable quiz platform supporting concurrent users
- Persistent data storage for analytics
- RESTful API for integration
- Containerized deployment for easy scaling

## Possible Extensions

1. **Time-Based Scoring**
   - Add timestamp tracking for answer submissions
   - Calculate time-weighted scores

2. **Complex Conditions**
   - Multiple score comparisons: `fruits >= 1 and apples > 0`
   - Range checks: `apples >= -5 and apples <= 5`

3. **Result Pages**
   - Different final messages based on score ranges
   - Personalized recommendations based on quiz outcomes

4. **Answer History**
   - Track all answers in session
   - Allow review before submission
   - Implement question navigation (back/forward)

5. **Analytics Dashboard**
   - Aggregate statistics across all sessions
   - Common paths through quiz
   - Average scores per question

## Conclusion

This use case demonstrates PyQuizHub's capability to handle complex quiz scenarios with:
- ✅ Multi-dimensional scoring
- ✅ Conditional branching logic
- ✅ Session state management
- ✅ Concurrent user support
- ✅ Flexible question flow control

The system successfully processes complex conditional logic, maintains isolated user sessions, and provides a robust platform for adaptive assessments and surveys.
