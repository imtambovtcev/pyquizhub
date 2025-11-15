# PyQuizHub Admin Web Interface

Standalone web interface for PyQuizHub administration.

## Overview

This is a **separate service** that provides a web-based interface for managing PyQuizHub:
- Runs on its own port (8081 by default)
- Independent from the user-facing web interface  
- Communicates with the core API via REST
- Requires admin authentication token

## Quick Start

### Standalone Mode

```bash
cd admin_web
pip install -r requirements.txt

# Set environment variables
export PYQUIZHUB_API_URL=http://localhost:8000
export PYQUIZHUB_ADMIN_TOKEN=your-secure-admin-token-here
export ADMIN_PORT=8081

# Run the server
python app.py
```

Access at: http://localhost:8081

### Docker Mode

The admin interface runs as a separate container in docker-compose:

```bash
docker compose up -d admin-web
```

Access at: http://localhost:8081

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYQUIZHUB_API_URL` | URL of the core API | `http://localhost:8000` |
| `PYQUIZHUB_ADMIN_TOKEN` | Admin authentication token | `your-secure-admin-token-here` |
| `ADMIN_PORT` | Port for admin interface | `8081` |
| `DEBUG` | Enable debug mode | `false` |

## Features

### Dashboard
- Live statistics (quizzes, tokens, users, sessions)
- System health monitoring
- Quick action shortcuts

### Quiz Management
- Create quizzes with JSON editor
- **Validate quiz structure** with comprehensive error reporting
  - Type checking for all variable definitions
  - Expression validation
  - API integration validation
  - Permission tier validation
- Load templates
- View all quizzes
- Edit existing quizzes
- Delete quizzes
- Generate tokens for quiz access

### Token Management
- Generate permanent/single-use tokens
- View all tokens
- Delete tokens
- Copy to clipboard

### User Management  
- View all users
- Add new users

### Results & Analytics
- View results by quiz or user
- Monitor completion rates

### Session Monitoring
- View active sessions
- Track user progress

## Architecture

```
admin_web/
├── app.py                 # Flask application
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── quizzes.html
│   └── create_quiz.html
└── static/                # CSS and JavaScript
    ├── css/
    │   └── admin.css
    └── js/
        └── admin-common.js
```

## API Communication

The admin interface proxies all requests to the core API:

```
Browser → Admin Web (Port 8081) → Core API (Port 8000)
```

All requests include the admin authentication token automatically.

## Security

- **Authentication**: All API requests require admin token
- **CORS**: Enabled for API communication
- **Input Validation**: Quiz JSON is validated before submission using comprehensive validator
  - Validates quiz structure and schema
  - Checks variable definitions and types
  - Validates expressions and conditions
  - Enforces permission tiers
  - Returns detailed error messages with context
- **XSS Prevention**: All user input is sanitized
- **Safe Evaluation**: Sandboxed expression execution
- **Rate Limiting**: Configurable limits for API calls

## Development

### Running Locally

```bash
cd admin_web
pip install -r requirements.txt
DEBUG=true python app.py
```

### Adding New Pages

1. Create HTML template in `templates/`
2. Add route in `app.py`
3. Add navigation link in `base.html`

### Customizing Styles

Edit `static/css/admin.css`. The design uses CSS variables for easy theming:

```css
:root {
    --primary-color: #2563eb;
    --secondary-color: #64748b;
    /* ... */
}
```

## Docker Integration

The admin interface is designed to run as a separate service in docker-compose:

```yaml
admin-web:
  build:
    context: .
    dockerfile: admin_web/Dockerfile
  ports:
    - "8081:8081"
  environment:
    - PYQUIZHUB_API_URL=http://api:8000
    - PYQUIZHUB_ADMIN_TOKEN=${PYQUIZHUB_ADMIN_TOKEN}
  depends_on:
    - api
  networks:
    - pyquizhub-network
```

## Troubleshooting

### Cannot Connect to API

Check:
1. API is running: `curl http://localhost:8000/health`
2. `PYQUIZHUB_API_URL` is correct
3. Network connectivity between containers

### Authentication Errors

Verify:
1. `PYQUIZHUB_ADMIN_TOKEN` matches the token in `.env`
2. Token hasn't expired (if using temporary tokens)

### Port Already in Use

Change the port:
```bash
export ADMIN_PORT=8082
python app.py
```

## Production Deployment

For production:

1. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Caddy)
2. **Secure Token**: Use a strong, randomly generated admin token
3. **Disable Debug**: Set `DEBUG=false`
4. **Network Isolation**: Use Docker networks to restrict access
5. **Access Control**: Add IP whitelisting or VPN requirement

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- JavaScript required
- Responsive design for mobile devices
