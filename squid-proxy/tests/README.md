# Squid Proxy Tests

This directory contains test scripts for validating the Squid Proxy add-on functionality.

## Setup

### 1. Install Dependencies

```bash
pip install python-dotenv curl-cffi requests
```

### 2. Configure Credentials

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual proxy credentials:

```bash
# Proxy authentication credentials
PROXY_USER=your_actual_username
PROXY_PASSWORD=your_actual_password

# Proxy URL (include protocol and port)
PROXY_URL=https://your-domain.com:3129
```

**⚠️ Security Note:** The `.env` file is automatically ignored by git to prevent accidentally committing credentials.

## Running Tests

### Basic Proxy Test

```bash
python test_proxy.py
```

This will:
- Create 10 concurrent connections
- Alternate between Google and httpbin.org
- Keep connections open for 2 seconds (visible in dashboard)
- Display response status and body snippets

## Test Configuration

The test script uses the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROXY_USER` | Proxy username (8-32 chars) | `squidadmin` |
| `PROXY_PASSWORD` | Proxy password (8+ chars) | `MySecurePass123` |
| `PROXY_URL` | Full proxy URL with protocol and port | `https://proxy.example.com:3129` |

## Troubleshooting

### "Missing required environment variables"
- Ensure `.env` file exists in the `tests/` directory
- Verify all three variables are set (no empty values)

### Connection errors
- Check that the proxy add-on is running
- Verify the proxy URL is correct (domain/IP and port)
- Ensure credentials match the add-on configuration

### SSL verification errors
- For self-signed certificates, you may need to disable verification
- For Let's Encrypt, ensure your domain is properly configured
