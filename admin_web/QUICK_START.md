# PyQuizHub Admin Web - Quick Start

## Access the Admin Interface

**URL**: http://localhost:8081

## Quick Commands

### Start/Stop
```bash
# Start all services (includes admin)
docker compose up -d

# Start only admin service
docker compose up -d admin-web

# Stop admin service
docker compose stop admin-web

# View logs
docker logs -f pyquizhub-admin-web-1

# Restart admin service
docker compose restart admin-web
```

### Testing
```bash
# Run test script
./admin_web/test_admin.sh

# Check if running
docker ps | grep admin-web

# Test health endpoint
curl http://localhost:8081/api/health
```

## Main Features

### 📊 Dashboard (http://localhost:8081/)
- View total quizzes, tokens, users, sessions
- System health status
- Quick action buttons

### 📝 Quiz Management (http://localhost:8081/quizzes)
- View all quizzes
- Generate tokens
- Delete quizzes
- Click "Create New Quiz" to add quizzes

### ➕ Create Quiz (http://localhost:8081/quiz/create)
1. Click "Load Template" for a starter quiz
2. Edit the JSON
3. Click "Validate" to check for errors
4. Click "Create Quiz" to save
5. Optionally generate a token immediately

## Creating Your First Quiz

1. Go to http://localhost:8081/quiz/create
2. Click "Load Template"
3. Modify the template:
   ```json
   {
     "metadata": {
       "title": "My First Quiz",
       "description": "A simple quiz",
       "author": "Admin",
       "version": "2.0"
     },
     "variables": {
       "correct": {
         "type": "integer",
         "mutable_by": ["engine"],
         "tags": ["score"]
       }
     },
     "questions": [
       {
         "id": 1,
         "data": {
           "text": "What is 2 + 2?",
           "type": "integer"
         },
         "score_updates": [
           {
             "condition": "answer == 4",
             "update": {"correct": "correct + 1"}
           }
         ]
       }
     ],
     "transitions": {
       "1": [{"expression": "true", "next_question_id": null}]
     }
   }
   ```
4. Click "Create Quiz"
5. Copy the generated quiz ID
6. Generate a token when prompted
7. Use the token to take the quiz!

## Generating Tokens

### From Quiz List
1. Go to "Quizzes" page
2. Find your quiz
3. Click "Generate Token"
4. Choose permanent or single-use
5. Copy the token

### After Creating Quiz
- System prompts you automatically
- Choose token type
- Token is displayed in a popup

## Environment Variables

Set in `.env` file:
```bash
PYQUIZHUB_ADMIN_TOKEN=your-secure-admin-token-here
```

## Troubleshooting

### Can't Connect to Admin Interface
```bash
# Check if container is running
docker ps | grep admin-web

# If not running, start it
docker compose up -d admin-web

# Check logs for errors
docker logs pyquizhub-admin-web-1
```

### "API Connection: Unhealthy"
```bash
# Check if API container is running
docker ps | grep pyquizhub-api

# Start API if needed
docker compose up -d api

# Verify API is accessible
curl http://localhost:8000/health
```

### Quiz Creation Fails
1. Click "Validate" first to see errors
2. Check quiz JSON is valid
3. Ensure all required fields are present
4. Check browser console for errors

## Service Architecture

```
Browser
  ↓
Admin Web (Port 8081)
  ↓ (Admin Token Auth)
Core API (Port 8000)
  ↓
Database (Port 5433)
```

## Default Credentials

- **Admin Token**: Set in `.env` as `PYQUIZHUB_ADMIN_TOKEN`
- **Default**: `your-secure-admin-token-here`

⚠️ **Change this in production!**

## Pages Available

| Page | URL | Status |
|------|-----|--------|
| Dashboard | / | ✅ Fully functional |
| Quizzes | /quizzes | ✅ Fully functional |
| Create Quiz | /quiz/create | ✅ Fully functional |
| Quiz Detail | /quiz/<id> | ✅ Basic view |
| Tokens | /tokens | 🚧 Placeholder |
| Users | /users | 🚧 Placeholder |
| Results | /results | 🚧 Placeholder |
| Sessions | /sessions | 🚧 Placeholder |

## Pro Tips

1. **Auto-save**: Quiz drafts are saved to localStorage automatically
2. **Keyboard Shortcuts**: Ctrl/Cmd + S to save (where applicable)
3. **Validation**: Always validate before creating a quiz
4. **Token Types**:
   - **Permanent**: Can be used multiple times
   - **Single-use**: Expires after one quiz session
5. **Copy Token**: Click to copy token to clipboard automatically

## Need Help?

- Check `admin_web/README.md` for detailed documentation
- Run `./admin_web/test_admin.sh` to verify setup
- Check logs: `docker logs pyquizhub-admin-web-1`
- Ensure API is running: `docker ps | grep api`
