# Structured JSON Logging Implementation

## Overview

This document describes the implementation of structured JSON logging for the FastAPI application. This change ensures all logs (application logs, uvicorn logs, and exception traces) are output as single-line JSON objects, making them easier to parse, search, and analyze in CloudWatch Logs.

## Problem

Previously, error logs from the FastAPI application were spread across multiple lines, making it difficult to:
- Parse logs programmatically
- Search for specific errors
- Correlate related log entries
- Create CloudWatch metrics and alarms based on log patterns

Example of the problematic multi-line format:
```
30 November 2025, 17:49
psycopg2.errors.StringDataRightTruncation: value too long for type character varying(15)
trigpointing-app
30 November 2025, 17:49
File "/usr/local/lib/python3.11/site-packages/starlette/middleware/errors.py", line 186, in __call__
trigpointing-app
30 November 2025, 17:49
await self.app(scope, receive_or_disconnect, send_no_error)
```

## Solution

Implemented structured JSON logging with the following components:

### 1. Enhanced JSON Formatter (`api/core/logging.py`)

- Added support for uvicorn-specific fields (`status_code`, `method`, `path`)
- Ensured exception traces are included as escaped strings (single-line JSON)
- Maintains human-readable format for development (`DEBUG=True`)
- Uses JSON format for production/staging (`DEBUG=False`)

### 2. Uvicorn Log Configuration

Created `get_uvicorn_log_config()` function that:
- Configures uvicorn's own loggers to use JSON format in production
- Maintains colorized output for development
- Ensures access logs and error logs both use structured format

### 3. Custom Startup Script (`api/start.py`)

- Replaces direct `uvicorn` command in Dockerfile
- Passes log configuration to uvicorn
- Ensures consistent logging across all parts of the application

### 4. Global Exception Handlers (`api/main.py`)

Added two exception handlers:
- `database_error_handler`: Specifically handles SQLAlchemy/psycopg2 errors
- `global_exception_handler`: Catches all other unhandled exceptions

Both handlers:
- Log exceptions with full context (request details, error type, stack trace)
- Return appropriate HTTP error responses
- Ensure exceptions don't bypass JSON logging

## Benefits

1. **Easier Log Analysis**: Each log entry is a single JSON line
2. **Better CloudWatch Integration**: Can create metrics and filters based on JSON fields
3. **Improved Debugging**: Full context (URL, method, error type) in each log entry
4. **Consistent Format**: All logs (app, uvicorn, exceptions) use the same structure
5. **Preserved Stack Traces**: Full exception traces included but as escaped strings

## Example JSON Log Entry

```json
{
  "timestamp": "2025-11-30 17:49:23",
  "level": "ERROR",
  "logger": "api.main",
  "message": "Database error: StringDataRightTruncation: value too long for type character varying(15)",
  "method": "POST",
  "url": "https://api.trigpointing.uk/v1/endpoint",
  "path": "/v1/endpoint",
  "client": "10.0.1.123",
  "db_error_type": "StringDataRightTruncation",
  "exc_type": "DataError",
  "exception": "Traceback (most recent call last):\\n  File ...\\"
}
```

## Files Changed

1. `api/core/logging.py`:
   - Enhanced `JSONFormatter` with additional fields
   - Added `get_uvicorn_log_config()` function

2. `api/start.py` (new file):
   - Startup script that configures uvicorn with JSON logging

3. `api/main.py`:
   - Added database error handler
   - Added global exception handler
   - Imported necessary exception types

4. `Dockerfile`:
   - Updated CMD to use `python api/start.py` instead of direct `uvicorn` command

## Deployment

The changes require rebuilding and redeploying the Docker image:

```bash
# Build and deploy
make deploy-production  # or deploy-staging
```

No infrastructure changes are required - the ECS task definition and CloudWatch Logs configuration remain unchanged.

## Testing

To verify JSON logging is working:

1. Check CloudWatch Logs for the FastAPI task
2. Look for single-line JSON entries instead of multi-line stack traces
3. Trigger an error and verify it's logged as JSON with full context

## Environment Variables

No new environment variables required. Behavior is controlled by existing `DEBUG` setting:
- `DEBUG=false` (production/staging): JSON format
- `DEBUG=true` (development): Human-readable format

## Backwards Compatibility

- Development environment (`DEBUG=true`) maintains human-readable format
- Production logs format changed, but CloudWatch Logs will handle both old and new formats
- No changes needed to log analysis tools (they should work better with JSON)
