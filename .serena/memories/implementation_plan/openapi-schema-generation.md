# OpenAPI Schema Generation CI/CD

## Goal
Auto-generate an OpenAPI 3.0 spec from Pretix's DRF viewsets/serializers using `drf-spectacular`,
and publish it as a GitHub Release asset so the gateway can fetch it dynamically.

## How It Works

### Architecture
```
Gultix CI (on push to main / tag)
  ├── Build Docker image (includes drf-spectacular)
  ├── Start postgres + redis service containers
  ├── Run Django migrations
  ├── Run generate_schema.py → pretix-openapi.yaml + .json
  └── Upload to GitHub Releases
        ↓
Gateway fetches:
  https://github.com/GDGBogor/gultix/releases/latest/download/pretix-openapi.yaml
```

### Files Added
- `generate_schema.py` — standalone script that:
  - Injects `drf_spectacular` into `INSTALLED_APPS` at runtime (no pretix settings changes)
  - Sets `DEFAULT_SCHEMA_CLASS` to `drf_spectacular.openapi.AutoSchema`
  - Configures `SPECTACULAR_SETTINGS` with Gultix metadata
  - Uses `SchemaGenerator().get_schema()` to produce the spec
  - Outputs YAML or JSON
- `.github/workflows/generate-openapi-schema.yml` — CI workflow

### CI Workflow Details
- **Trigger**: push to main/master, tags `v*.*.*`, or manual dispatch
- **Services**: postgres:17 + redis:latest (with health checks)
- **Steps**:
  1. Build Gultix Docker image (with drf-spectacular installed)
  2. Run `pretix migrate` to set up database schema
  3. Run `generate_schema.py` → YAML and JSON output
  4. Upload as GitHub artifact
  5. Create/update GitHub Release with schema files

### Dockerfile Change
- Added `drf-spectacular` to the `pip install` line
- It's installed in the image but not active at runtime (not in pretix's `INSTALLED_APPS`)
- Only used by `generate_schema.py` during CI

### Limitations / Watch Items
- drf-spectacular inspects code-level definitions — custom pretix serializer behavior
  (dynamic fields, conditional responses) may produce incomplete schemas
- Plugin endpoints (Midtrans, Bevy, Google Font) will appear IF they use standard DRF patterns
- Expected accuracy: ~80-90% out of the box; can improve with `@extend_schema` decorators
- When pretix updates: re-run CI → new spec generated automatically

### Testing Locally
```bash
# Start services
docker compose up -d postgres redis

# Build image
docker build --build-arg GITHUB_TOKEN=<token> --target pretix-build -t gultix-local .

# Run migrations
docker run --rm --network host \
  -e PRETIX_DATABASE_BACKEND=postgresql \
  -e PRETIX_DATABASE_HOST=localhost \
  -e PRETIX_DATABASE_NAME=<db> \
  -e PRETIX_DATABASE_USER=<user> \
  -e PRETIX_DATABASE_PASSWORD=<pass> \
  -e PRETIX_REDIS_LOCATION=redis://localhost:6379/1 \
  -e PRETIX_CELERY_BACKEND=redis://localhost:6379/2 \
  -e PRETIX_CELERY_BROKER=redis://localhost:6379/3 \
  -e PRETIX_PRETIX_URL=http://localhost \
  gultix-local migrate

# Generate schema
docker run --rm --network host \
  -e PRETIX_DATABASE_BACKEND=postgresql \
  -e PRETIX_DATABASE_HOST=localhost \
  -e PRETIX_DATABASE_NAME=<db> \
  -e PRETIX_DATABASE_USER=<user> \
  -e PRETIX_DATABASE_PASSWORD=<pass> \
  -e PRETIX_REDIS_LOCATION=redis://localhost:6379/1 \
  -e PRETIX_CELERY_BACKEND=redis://localhost:6379/2 \
  -e PRETIX_CELERY_BROKER=redis://localhost:6379/3 \
  -e PRETIX_PRETIX_URL=http://localhost \
  -v $(pwd)/generate_schema.py:/generate_schema.py:ro \
  -v $(pwd)/output:/output \
  --entrypoint python \
  gultix-local /generate_schema.py --output /output/pretix-openapi.yaml
```
