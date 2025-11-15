# PyQuizHub SSRF & API Security Architecture

## Executive Summary

This document outlines a **defense-in-depth** security architecture for PyQuizHub's API integration system, addressing Server-Side Request Forgery (SSRF), privilege escalation, and abuse vectors. The goal is to enable safe user-generated quiz content with external API calls while preventing attackers from compromising the system or using it as an attack proxy.

## Threat Model

### Attack Vectors

1. **SSRF (Server-Side Request Forgery)**
   - Target internal services: `http://localhost:8000/admin/delete_all`
   - Cloud metadata: `http://169.254.169.254/latest/meta-data`
   - Internal network: `http://10.0.0.1/admin-panel`
   - Redirect chains: `http://evil.com/redirect-to-localhost`

2. **Privilege Escalation**
   - Quiz creator calls admin-only FastAPI routes
   - Access environment variables via SSRF
   - Read system files via file:// URLs
   - Bypass authentication via internal routes

3. **Abuse & DoS**
   - Use server as proxy to attack other sites
   - Infinite request loops (quiz calls itself)
   - Large response bodies (100GB+ to exhaust memory)
   - Slow-loris style attacks (slow responses)
   - Request flooding (10000 requests per quiz)

4. **Data Exfiltration**
   - Extract internal data via DNS queries
   - Timing attacks to probe internal network
   - Error message exploitation
   - Response header leakage

### Attacker Capabilities

**Assumption**: Quiz creators are **untrusted** and may be malicious.

They can:
- Create arbitrary quiz JSON
- Specify API URLs, headers, bodies
- Control timing of requests
- Read API responses
- Create loops and conditionals

They **cannot** (must prevent):
- Execute arbitrary code on server
- Access internal network
- Call admin routes
- Bypass rate limits
- Read server files
- Access other users' data

---

## Security Architecture Layers

```
┌────────────────────────────────────────────────────────────┐
│                     Layer 7: Monitoring                     │
│  • Audit logging                                           │
│  • Anomaly detection                                       │
│  • Alert on suspicious patterns                            │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│                  Layer 6: Rate Limiting                     │
│  • Per-quiz limits                                         │
│  • Per-user limits                                         │
│  • Global limits                                           │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Layer 5: Request Execution                     │
│  • Timeout enforcement                                     │
│  • Size limits                                             │
│  • Redirect blocking                                       │
│  • Safe HTTP client configuration                          │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│           Layer 4: DNS Resolution Validation                │
│  • Resolve DNS                                             │
│  • Check resolved IP against blacklist                     │
│  • Reject private/local IPs                                │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Layer 3: URL Allowlist System                  │
│  • Check against approved domains                          │
│  • Validate URL structure                                  │
│  • Enforce HTTPS only                                      │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│            Layer 2: Input Validation & Parsing              │
│  • Parse URL safely                                        │
│  • Reject IP-based URLs                                    │
│  • Reject file:// gopher:// etc.                           │
│  • Validate hostname format                                │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│              Layer 1: Quiz Definition Validation            │
│  • Validate API config structure                           │
│  • Check against quota limits                              │
│  • Verify creator permissions                              │
└────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Layer 1: Quiz Definition Validation

**Purpose**: Reject malicious quiz definitions at upload time

```python
class APIConfigValidator:
    """Validates API integration configs in quiz definitions."""

    MAX_API_INTEGRATIONS_PER_QUIZ = 5
    ALLOWED_HTTP_METHODS = ["GET", "POST"]  # No PUT, DELETE, PATCH

    @staticmethod
    def validate_api_config(api_config: dict, creator_permissions: dict) -> None:
        """
        Validate API integration configuration.

        Args:
            api_config: API configuration from quiz
            creator_permissions: Creator's permission level

        Raises:
            ValueError: If configuration is invalid or not allowed
        """
        # Check creator has permission to use APIs
        if not creator_permissions.get("can_use_external_apis", False):
            raise ValueError("Creator does not have permission to use external APIs")

        # Validate structure
        required_fields = ["id", "url", "method"]
        for field in required_fields:
            if field not in api_config:
                raise ValueError(f"Missing required field: {field}")

        # Validate HTTP method
        method = api_config["method"].upper()
        if method not in APIConfigValidator.ALLOWED_HTTP_METHODS:
            raise ValueError(
                f"HTTP method {method} not allowed. "
                f"Only {APIConfigValidator.ALLOWED_HTTP_METHODS} permitted"
            )

        # Validate URL is not obviously malicious
        url = api_config["url"]
        if not url.startswith("https://"):
            raise ValueError("Only HTTPS URLs are allowed")

        # No template variables in base URL (prevent SSRF via template injection)
        if "{" in url or "$" in url:
            raise ValueError(
                "Template variables not allowed in base URL. "
                "Use query parameters or body for dynamic data"
            )

        # Check creator's API allowlist
        allowed_domains = creator_permissions.get("allowed_api_domains", [])
        if not APIConfigValidator._is_domain_allowed(url, allowed_domains):
            raise ValueError(
                f"Domain not in creator's allowlist: {allowed_domains}"
            )

    @staticmethod
    def _is_domain_allowed(url: str, allowed_domains: list) -> bool:
        """Check if URL's domain is in allowlist."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        hostname = parsed.hostname

        for allowed in allowed_domains:
            if allowed.startswith("*."):
                # Wildcard subdomain
                if hostname.endswith(allowed[2:]):
                    return True
            elif hostname == allowed:
                return True

        return False
```

### Layer 2: Input Validation & Parsing

**Purpose**: Reject dangerous URL patterns

```python
class URLValidator:
    """Validates URLs against SSRF attack patterns."""

    # Blocked URL schemes
    BLOCKED_SCHEMES = [
        "file", "ftp", "gopher", "dict", "jar", "tftp",
        "ldap", "ldaps", "imap", "imaps", "smtp", "smtps"
    ]

    # Private IP ranges (IPv4)
    PRIVATE_IP_RANGES = [
        ("127.0.0.0", "127.255.255.255"),      # Loopback
        ("10.0.0.0", "10.255.255.255"),        # Private class A
        ("172.16.0.0", "172.31.255.255"),      # Private class B
        ("192.168.0.0", "192.168.255.255"),    # Private class C
        ("169.254.0.0", "169.254.255.255"),    # Link-local
        ("0.0.0.0", "0.255.255.255"),          # Current network
        ("224.0.0.0", "255.255.255.255"),      # Multicast & reserved
    ]

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate URL for SSRF attacks.

        Args:
            url: URL to validate

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is potentially malicious
        """
        from urllib.parse import urlparse
        import ipaddress

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

        # Check scheme
        if parsed.scheme.lower() not in ["https"]:
            raise ValueError(f"Only HTTPS scheme allowed, got: {parsed.scheme}")

        # Check for blocked schemes
        if parsed.scheme.lower() in URLValidator.BLOCKED_SCHEMES:
            raise ValueError(f"Blocked URL scheme: {parsed.scheme}")

        # Check hostname exists
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")

        # Reject IP-based URLs (IPv4 and IPv6)
        hostname = parsed.hostname.lower()

        # Check for IPv4
        try:
            ip = ipaddress.ip_address(hostname)
            raise ValueError(f"IP-based URLs not allowed: {hostname}")
        except ValueError:
            pass  # Not an IP, good

        # Check for IPv6 (in brackets)
        if hostname.startswith("[") and hostname.endswith("]"):
            raise ValueError(f"IPv6 URLs not allowed: {hostname}")

        # Check for localhost variations
        localhost_variants = [
            "localhost", "127.0.0.1", "::1", "0.0.0.0",
            "0177.0.0.1",  # Octal
            "0x7f.0.0.1",  # Hex
        ]
        if hostname in localhost_variants:
            raise ValueError(f"Localhost URLs not allowed: {hostname}")

        # Check for internal TLDs
        internal_tlds = [".local", ".internal", ".lan", ".corp"]
        if any(hostname.endswith(tld) for tld in internal_tlds):
            raise ValueError(f"Internal TLD not allowed: {hostname}")

        # Check for auth in URL (can leak credentials)
        if parsed.username or parsed.password:
            raise ValueError("URLs with authentication not allowed")

        # Check for @-based SSRF tricks: http://victim.com@attacker.com
        if "@" in url:
            raise ValueError("@ character not allowed in URLs")

        return url

    @staticmethod
    def is_private_ip(ip_str: str) -> bool:
        """Check if IP is in private range."""
        import ipaddress

        try:
            ip = ipaddress.ip_address(ip_str)

            # Check if private
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return True

            # Additional check for cloud metadata
            if ip_str == "169.254.169.254":
                return True

            return False

        except ValueError:
            return False
```

### Layer 3: URL Allowlist System

**Purpose**: Only allow requests to approved external services

```python
class APIAllowlistManager:
    """Manages allowed external API domains."""

    def __init__(self):
        # Global allowlist (platform-approved APIs)
        self.global_allowlist = [
            "api.openweathermap.org",
            "api.open-meteo.com",
            "api.weatherapi.com",
            "restcountries.com",
            "api.github.com",
            "httpbin.org",  # For testing only
        ]

        # Creator-specific allowlists (stored in database)
        # Format: {creator_id: [domain1, domain2, ...]}
        self.creator_allowlists = {}

    def is_allowed(self, url: str, creator_id: str) -> bool:
        """
        Check if URL is allowed for creator.

        Args:
            url: Full URL to check
            creator_id: Quiz creator's ID

        Returns:
            True if allowed, False otherwise
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = parsed.hostname

        # Check global allowlist
        if self._match_domain(hostname, self.global_allowlist):
            return True

        # Check creator-specific allowlist
        creator_domains = self.creator_allowlists.get(creator_id, [])
        if self._match_domain(hostname, creator_domains):
            return True

        return False

    def _match_domain(self, hostname: str, allowlist: list) -> bool:
        """Match hostname against allowlist with wildcard support."""
        for allowed in allowlist:
            if allowed.startswith("*."):
                # Wildcard subdomain: *.example.com
                base_domain = allowed[2:]
                if hostname == base_domain or hostname.endswith("." + base_domain):
                    return True
            elif hostname == allowed:
                return True

        return False

    def request_domain_approval(
        self,
        creator_id: str,
        domain: str,
        justification: str
    ) -> str:
        """
        Request approval for a new domain (requires admin approval).

        Args:
            creator_id: Creator requesting access
            domain: Domain to add
            justification: Why this domain is needed

        Returns:
            Request ID for tracking
        """
        # This would create a pending approval request
        # Admins review and approve/reject
        # Implemented in database
        pass
```

### Layer 4: DNS Resolution Validation

**Purpose**: Prevent DNS rebinding and internal IP targeting

```python
import socket
import ipaddress
from typing import Tuple

class DNSValidator:
    """Validates DNS resolution to prevent SSRF via DNS."""

    @staticmethod
    def resolve_and_validate(hostname: str) -> Tuple[str, bool]:
        """
        Resolve hostname and validate IP is not private.

        Args:
            hostname: Hostname to resolve

        Returns:
            Tuple of (resolved_ip, is_safe)

        Raises:
            ValueError: If DNS resolution fails or resolves to private IP
        """
        try:
            # Resolve hostname to IP
            resolved_ip = socket.gethostbyname(hostname)

            # Check if IP is private/internal
            if URLValidator.is_private_ip(resolved_ip):
                raise ValueError(
                    f"Hostname {hostname} resolves to private IP: {resolved_ip}"
                )

            # Additional cloud metadata check
            if resolved_ip == "169.254.169.254":
                raise ValueError(
                    f"Hostname {hostname} resolves to cloud metadata service"
                )

            # Check for IPv6 resolution too
            try:
                ipv6_info = socket.getaddrinfo(
                    hostname, None, socket.AF_INET6
                )
                for info in ipv6_info:
                    ipv6_addr = info[4][0]
                    ip_obj = ipaddress.ip_address(ipv6_addr)
                    if ip_obj.is_private or ip_obj.is_loopback:
                        raise ValueError(
                            f"Hostname {hostname} has private IPv6: {ipv6_addr}"
                        )
            except socket.gaierror:
                pass  # No IPv6, that's fine

            return resolved_ip, True

        except socket.gaierror as e:
            raise ValueError(f"Failed to resolve hostname {hostname}: {e}")

    @staticmethod
    def check_redirect_target(redirect_url: str) -> None:
        """
        Validate redirect target URL.

        This prevents bypass via redirect chains:
        https://safe.com/redirect -> http://localhost/admin

        Args:
            redirect_url: Target of HTTP redirect

        Raises:
            ValueError: If redirect target is not safe
        """
        # Apply all the same validations
        URLValidator.validate_url(redirect_url)

        # Check hostname resolution
        from urllib.parse import urlparse
        parsed = urlparse(redirect_url)
        if parsed.hostname:
            DNSValidator.resolve_and_validate(parsed.hostname)
```

### Layer 5: Request Execution (Safe HTTP Client)

**Purpose**: Execute requests with strict safety controls

```python
import requests
from typing import Dict, Any, Optional
import time

class SafeHTTPClient:
    """HTTP client with SSRF protections."""

    def __init__(self):
        self.timeout = (3, 5)  # (connect, read) timeout in seconds
        self.max_response_size = 2 * 1024 * 1024  # 2MB
        self.max_redirects = 0  # No redirects allowed
        self.user_agent = "PyQuizHub/1.0 (Security-Hardened)"

    def make_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        creator_id: str = None
    ) -> requests.Response:
        """
        Make HTTP request with full SSRF protection.

        Args:
            method: HTTP method (GET, POST)
            url: Target URL (must be pre-validated)
            headers: Request headers
            body: Request body (for POST)
            creator_id: Quiz creator ID (for allowlist check)

        Returns:
            Response object

        Raises:
            ValueError: If request violates security policy
            requests.RequestException: If request fails
        """
        # Layer 2: URL validation
        URLValidator.validate_url(url)

        # Layer 3: Allowlist check
        if creator_id:
            allowlist = APIAllowlistManager()
            if not allowlist.is_allowed(url, creator_id):
                raise ValueError(f"URL not in allowlist for creator {creator_id}")

        # Layer 4: DNS validation
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.hostname:
            DNSValidator.resolve_and_validate(parsed.hostname)

        # Prepare safe request configuration
        safe_headers = headers.copy() if headers else {}
        safe_headers["User-Agent"] = self.user_agent

        # Remove dangerous headers
        dangerous_headers = ["X-Forwarded-For", "X-Forwarded-Host", "Host"]
        for h in dangerous_headers:
            safe_headers.pop(h, None)

        # Configure session with safety limits
        session = requests.Session()
        session.max_redirects = self.max_redirects

        try:
            # Make request
            response = session.request(
                method=method,
                url=url,
                headers=safe_headers,
                json=body,
                timeout=self.timeout,
                allow_redirects=False,  # Critical: no redirects
                stream=False,  # Load entire response
                verify=True,  # Verify SSL certificates
            )

            # Check response size
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_response_size:
                raise ValueError(
                    f"Response too large: {content_length} bytes > "
                    f"{self.max_response_size} bytes"
                )

            # Check actual content size
            if len(response.content) > self.max_response_size:
                raise ValueError(
                    f"Response content exceeds size limit: "
                    f"{len(response.content)} bytes"
                )

            return response

        except requests.Timeout:
            raise ValueError(f"Request timeout after {self.timeout} seconds")
        except requests.TooManyRedirects:
            raise ValueError("Redirect detected (redirects not allowed)")
        except requests.RequestException as e:
            # Generic error - don't leak details
            raise ValueError(f"Request failed: external API error")
```

### Layer 6: Rate Limiting

**Purpose**: Prevent abuse and DoS

```python
from datetime import datetime, timedelta
from collections import defaultdict
import threading

class RateLimiter:
    """Rate limiter for API requests."""

    def __init__(self):
        self.lock = threading.Lock()

        # Per-quiz limits
        self.quiz_requests = defaultdict(list)  # {quiz_id: [timestamp, ...]}
        self.quiz_limit = 10  # requests per quiz execution

        # Per-creator limits
        self.creator_requests = defaultdict(list)  # {creator_id: [timestamp, ...]}
        self.creator_limit_per_minute = 60
        self.creator_limit_per_hour = 500

        # Per-user limits (quiz taker)
        self.user_requests = defaultdict(list)
        self.user_limit_per_minute = 10

        # Global limits
        self.global_requests = []
        self.global_limit_per_second = 100

    def check_limit(
        self,
        quiz_id: str,
        creator_id: str,
        user_id: str,
        session_id: str
    ) -> bool:
        """
        Check if request is within rate limits.

        Args:
            quiz_id: Quiz being executed
            creator_id: Quiz creator
            user_id: User taking quiz
            session_id: Quiz session ID

        Returns:
            True if allowed, False if rate limited

        Raises:
            ValueError: If rate limit exceeded
        """
        with self.lock:
            now = datetime.now()

            # Check per-session limit (prevent loops)
            session_key = f"{session_id}:{quiz_id}"
            if len(self.quiz_requests[session_key]) >= self.quiz_limit:
                raise ValueError(
                    f"Rate limit exceeded: max {self.quiz_limit} requests per quiz session"
                )

            # Check per-creator limits
            self._clean_old_requests(self.creator_requests[creator_id], minutes=60)
            recent_minute = [
                ts for ts in self.creator_requests[creator_id]
                if now - ts < timedelta(minutes=1)
            ]
            if len(recent_minute) >= self.creator_limit_per_minute:
                raise ValueError(
                    f"Creator rate limit exceeded: "
                    f"{self.creator_limit_per_minute} requests/minute"
                )

            if len(self.creator_requests[creator_id]) >= self.creator_limit_per_hour:
                raise ValueError(
                    f"Creator rate limit exceeded: "
                    f"{self.creator_limit_per_hour} requests/hour"
                )

            # Check per-user limits
            self._clean_old_requests(self.user_requests[user_id], minutes=1)
            if len(self.user_requests[user_id]) >= self.user_limit_per_minute:
                raise ValueError(
                    f"User rate limit exceeded: "
                    f"{self.user_limit_per_minute} requests/minute"
                )

            # Check global limit
            self._clean_old_requests(self.global_requests, seconds=1)
            if len(self.global_requests) >= self.global_limit_per_second:
                raise ValueError(
                    f"System rate limit exceeded: "
                    f"{self.global_limit_per_second} requests/second"
                )

            # Record this request
            self.quiz_requests[session_key].append(now)
            self.creator_requests[creator_id].append(now)
            self.user_requests[user_id].append(now)
            self.global_requests.append(now)

            return True

    def _clean_old_requests(
        self,
        requests_list: list,
        minutes: int = 0,
        seconds: int = 0
    ) -> None:
        """Remove timestamps older than specified time."""
        now = datetime.now()
        cutoff = now - timedelta(minutes=minutes, seconds=seconds)
        requests_list[:] = [ts for ts in requests_list if ts > cutoff]
```

### Layer 7: Monitoring & Audit Logging

**Purpose**: Detect and respond to attacks

```python
import logging
from datetime import datetime
from enum import Enum

class SecurityEvent(str, Enum):
    SSRF_ATTEMPT = "ssrf_attempt"
    RATE_LIMIT_HIT = "rate_limit_hit"
    FORBIDDEN_DOMAIN = "forbidden_domain"
    PRIVATE_IP_DETECTED = "private_ip_detected"
    SUSPICIOUS_PATTERN = "suspicious_pattern"

class SecurityAuditor:
    """Audit logging for security events."""

    def __init__(self):
        self.logger = logging.getLogger("security_audit")
        self.alert_threshold = 5  # Alert after N violations in short time

    def log_security_event(
        self,
        event_type: SecurityEvent,
        creator_id: str,
        quiz_id: str,
        details: dict
    ) -> None:
        """
        Log security event.

        Args:
            event_type: Type of security event
            creator_id: Quiz creator ID
            quiz_id: Quiz ID
            details: Event details
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "creator_id": creator_id,
            "quiz_id": quiz_id,
            "details": details,
        }

        # Log to file
        self.logger.warning(f"SECURITY_EVENT: {event}")

        # Store in database for analysis
        self._store_event(event)

        # Check if creator should be flagged
        if self._should_flag_creator(creator_id):
            self._flag_creator(creator_id)

    def _store_event(self, event: dict) -> None:
        """Store event in database for analysis."""
        # TODO: Implement database storage
        pass

    def _should_flag_creator(self, creator_id: str) -> bool:
        """Check if creator has too many violations."""
        # TODO: Query recent violations
        return False

    def _flag_creator(self, creator_id: str) -> None:
        """Flag creator for review."""
        # TODO: Implement flagging system
        # - Disable API access
        # - Send alert to admins
        # - Require manual review
        pass
```

---

## Additional Security Measures

### 1. Network Isolation

**Recommendation**: Run quiz execution in isolated container/network

```yaml
# docker-compose.yml
services:
  quiz-executor:
    image: pyquizhub-executor
    networks:
      - quiz-network
    # No access to host network
    network_mode: "bridge"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
```

### 2. Route Separation

```python
# main.py - Separate routers by privilege level

# Public routes (no auth required)
app.include_router(public_router, prefix="/public")

# User routes (basic auth)
app.include_router(user_router, prefix="/quiz")

# Creator routes (creator auth)
app.include_router(creator_router, prefix="/creator")

# Admin routes (admin auth + IP whitelist)
app.include_router(admin_router, prefix="/admin")

# Internal routes (localhost only)
app.include_router(internal_router, prefix="/internal", dependencies=[localhost_only])

def localhost_only(request: Request):
    """Only allow requests from localhost."""
    client_host = request.client.host
    if client_host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Internal API")
```

### 3. Error Message Sanitization

```python
class SafeErrorResponse:
    """Sanitize error messages to prevent information leakage."""

    @staticmethod
    def sanitize_error(error: Exception) -> dict:
        """
        Convert exception to safe error response.

        Args:
            error: Exception to sanitize

        Returns:
            Safe error dict
        """
        # Never expose:
        # - Stack traces
        # - File paths
        # - Internal IPs
        # - SQL queries
        # - Environment variables

        # Generic error messages
        error_messages = {
            requests.Timeout: "External API request timed out",
            requests.ConnectionError: "Failed to connect to external API",
            ValueError: "Invalid request",
            PermissionError: "Access denied",
        }

        error_type = type(error)
        safe_message = error_messages.get(error_type, "An error occurred")

        return {
            "error": safe_message,
            "timestamp": datetime.now().isoformat(),
            "request_id": generate_request_id(),
        }
```

---

## Testing Strategy

### SSRF Test Suite

```python
# tests/test_security/test_ssrf_protection.py

def test_localhost_rejection():
    """Test that localhost URLs are rejected."""
    urls = [
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://127.1/admin",
        "http://0.0.0.0/admin",
        "http://[::1]/admin",
    ]
    for url in urls:
        with pytest.raises(ValueError):
            URLValidator.validate_url(url)

def test_private_ip_rejection():
    """Test that private IPs are rejected."""
    urls = [
        "http://10.0.0.1/data",
        "http://192.168.1.1/admin",
        "http://172.16.0.1/api",
    ]
    for url in urls:
        with pytest.raises(ValueError):
            URLValidator.validate_url(url)

def test_cloud_metadata_rejection():
    """Test that cloud metadata is rejected."""
    url = "http://169.254.169.254/latest/meta-data"
    with pytest.raises(ValueError):
        URLValidator.validate_url(url)

def test_dns_rebinding_protection():
    """Test that DNS rebinding is caught."""
    # Mock DNS to resolve to private IP
    # Verify rejection
    pass

def test_redirect_blocking():
    """Test that redirects are blocked."""
    # Make request that would redirect
    # Verify it's blocked
    pass
```

---

## Deployment Checklist

- [ ] Implement all 7 security layers
- [ ] Configure URL allowlist
- [ ] Set up rate limiting
- [ ] Enable audit logging
- [ ] Configure network isolation
- [ ] Separate admin routes
- [ ] Test SSRF protection
- [ ] Test rate limiting
- [ ] Set up monitoring alerts
- [ ] Review creator permissions system
- [ ] Penetration testing
- [ ] Security audit

---

## Next Steps

1. Implement `SafeHTTPClient` with all protections
2. Create URL allowlist management system
3. Add rate limiting to API integration
4. Implement audit logging
5. Write comprehensive security tests
6. Set up monitoring and alerting
7. Create creator permission system
8. Document security policies for quiz creators

This architecture provides **defense-in-depth** against SSRF and related attacks while still allowing legitimate external API usage.
