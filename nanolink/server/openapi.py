"""OpenAPI 3.0.3 specification and interactive Swagger UI generator."""

from __future__ import annotations

import json
from typing import Any, Dict
from nanolink import __version__

OPENAPI_SPEC: Dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {
        "title": "Nanolink API",
        "description": "High-performance, collision-resistant URL shortener & analytics engine.",
        "version": __version__,
        "contact": {
            "name": "Yashu Raghuvanshi",
            "url": "https://github.com/yashuraghuvanshi4-pixel/nanolink",
        },
    },
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {
                    "200": {
                        "description": "Server is healthy",
                        "content": {
                            "application/json": {
                                "example": {"status": "ok", "version": __version__}
                            }
                        },
                    }
                },
            }
        },
        "/metrics": {
            "get": {
                "summary": "Prometheus metrics",
                "responses": {
                    "200": {
                        "description": "Prometheus-compatible scrape endpoint",
                        "content": {"text/plain": {}},
                    }
                },
            }
        },
        "/api/shorten": {
            "post": {
                "summary": "Shorten a destination URL",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["url"],
                                "properties": {
                                    "url": {"type": "string", "example": "https://github.com"},
                                    "alias": {"type": "string", "example": "my-repo"},
                                    "title": {"type": "string", "example": "My Repository"},
                                    "ttl_seconds": {"type": "integer", "example": 86400},
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "example": ["tech", "git"],
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Link created successfully"},
                    "400": {"description": "Validation or safety check error"},
                    "409": {"description": "Custom alias already exists"},
                },
            }
        },
        "/api/bulk-shorten": {
            "post": {
                "summary": "Bulk shorten multiple URLs",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["items"],
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["url"],
                                            "properties": {
                                                "url": {"type": "string"},
                                                "alias": {"type": "string"},
                                            },
                                        },
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Batch processing completed"},
                    "400": {"description": "Invalid batch structure"},
                },
            }
        },
        "/api/stats/{code}": {
            "get": {
                "summary": "Get real-time analytics for short code",
                "parameters": [
                    {
                        "name": "code",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {"description": "Analytics breakdown and click metrics"},
                    "404": {"description": "Link not found"},
                },
            }
        },
        "/api/stats/{code}/export": {
            "get": {
                "summary": "Export clickstream events",
                "parameters": [
                    {
                        "name": "code",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "format",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["csv", "json"], "default": "csv"},
                    },
                ],
                "responses": {
                    "200": {"description": "CSV or JSON click stream"},
                },
            }
        },
        "/api/search": {
            "get": {
                "summary": "Search links",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 50},
                    },
                ],
                "responses": {
                    "200": {"description": "Matched links"},
                },
            }
        },
        "/{code}": {
            "get": {
                "summary": "Redirect to destination URL",
                "parameters": [
                    {
                        "name": "code",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "307": {"description": "Temporary redirect to target URL"},
                    "404": {"description": "Code not found"},
                    "410": {"description": "Link expired"},
                },
            }
        },
    },
}

SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Nanolink API Documentation</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body { margin: 0; background-color: #0b0f19; color: #fff; }
    .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
    .swagger-ui .topbar { display: none; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout"
      });
    };
  </script>
</body>
</html>
"""
