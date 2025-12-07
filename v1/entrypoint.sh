#!/bin/bash
set -e

echo "🚀 Starting Bot Builder Application..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if pg_isready -h db -U botbuilder -d botbuilder > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - PostgreSQL not ready yet..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Failed to connect to PostgreSQL after $max_attempts attempts"
    exit 1
fi

# Run database migrations
echo "🔄 Running database migrations..."
if alembic upgrade head; then
    echo "✅ Migrations completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Start the application
echo "🎉 Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000