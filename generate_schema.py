#!/usr/bin/env python
"""
Generate OpenAPI schema from Pretix using drf-spectacular.

This script is intended to run inside the Gultix Docker container during CI/CD.
It configures drf-spectacular at runtime (without modifying pretix's settings),
then introspects all DRF viewsets and serializers to produce an OpenAPI 3.0 spec.

Usage:
    python generate_schema.py [--output schema.yml] [--format yaml|json]
"""

import argparse
import json
import os
import sys


def setup_django():
    """Initialize Django with drf-spectacular injected into settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pretix.settings")

    import django
    from django.conf import settings

    # Inject drf-spectacular into the already-configured settings
    if "drf_spectacular" not in settings.INSTALLED_APPS:
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS) + ["drf_spectacular"]

    # Set drf-spectacular as the default schema class for DRF
    if not hasattr(settings, "REST_FRAMEWORK"):
        settings.REST_FRAMEWORK = {}
    settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = (
        "drf_spectacular.openapi.AutoSchema"
    )

    # Configure drf-spectacular settings
    settings.SPECTACULAR_SETTINGS = {
        "TITLE": "Pretix API (Gultix)",
        "DESCRIPTION": (
            "Auto-generated OpenAPI schema for the Pretix ticketing platform, "
            "including GDG Bogor plugins (Midtrans, Google Font, Bevy integration)."
        ),
        "VERSION": getattr(settings, "PRETIX_VERSION", "1.0.0"),
        "SERVE_INCLUDE_SCHEMA": False,
        "SCHEMA_PATH_PREFIX": "/api/v1",
        # Be lenient with schema generation — pretix has complex serializers
        "ENUM_NAME_OVERRIDES": {},
        "COMPONENT_SPLIT_REQUEST": True,
        "SORT_OPERATIONS": True,
    }

    django.setup()


def generate_schema(output_format="yaml"):
    """Generate the OpenAPI schema."""
    from drf_spectacular.generators import SchemaGenerator

    # In Pretix, the API is mounted under /api/v1/ and the viewsets might only be
    # discovered properly if we use the root urlconf or specific api urlconf.
    # drf-spectacular uses `django.conf.settings.ROOT_URLCONF` by default, but Pretix
    # has a complex multidomain setup that might mask the API routes from the default generator.
    generator = SchemaGenerator(urlconf='pretix.urls', api_version='v1')
    schema = generator.get_schema(public=True)

    # Try alternative urlconf if paths are empty
    if not schema or not schema.get('paths'):
        print('Retrying with specific urlconf...', file=sys.stderr)
        generator = SchemaGenerator(urlconf='pretix.api.urls', api_version='v1')
    schema = generator.get_schema(public=True)

    if output_format == "json":
        return json.dumps(schema, indent=2, default=str)
    else:
        try:
            import yaml

            return yaml.dump(schema, default_flow_style=False, allow_unicode=True)
        except ImportError:
            # Fallback to JSON if PyYAML not available
            print(
                "WARNING: PyYAML not installed, falling back to JSON format",
                file=sys.stderr,
            )
            return json.dumps(schema, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema from Pretix"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="pretix-openapi.yaml",
        help="Output file path (default: pretix-openapi.yaml)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    args = parser.parse_args()

    print("Setting up Django with drf-spectacular...", file=sys.stderr)
    setup_django()

    print("Generating OpenAPI schema...", file=sys.stderr)
    schema_content = generate_schema(args.format)

    if args.output == "-":
        print(schema_content)
    else:
        with open(args.output, "w") as f:
            f.write(schema_content)
        print(f"Schema written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
