#!/bin/sh
set -eu
python - <<'PY'
import time
from sqlalchemy import create_engine, text
from app.config import settings
for attempt in range(60):
    try:
        engine=create_engine(settings.database_url,pool_pre_ping=True)
        with engine.connect() as c:
            c.execute(text('SELECT 1'))
        print('Database is ready')
        break
    except Exception as exc:
        if attempt==59:
            raise
        print(f'Waiting for database: {exc}')
        time.sleep(2)
PY
alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers
