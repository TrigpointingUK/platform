"""
Test-session environment, loaded by pytest before api/tests/conftest.py (and
so before anything imports api settings).

Never let tests reach a real Redis. .env points REDIS_URL at localhost:6379,
which is often the SSM tunnel to the shared Valkey, so a bare `pytest` run
would cache test-fixture responses there (in 2026-10 this replaced the local
dev-stack's trig type list with test data). Env vars take precedence over
.env. Tests that exercise Redis patch settings themselves.
"""

import os

os.environ["CACHE_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""
