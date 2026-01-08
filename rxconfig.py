"""Reflex configuration for noGojira."""

import reflex as rx

config = rx.Config(
    app_name="nogojira",
    api_url="http://localhost:8000",
    backend_port=8000,
    frontend_port=3000,
    backend_host="0.0.0.0",
    db_url="sqlite:///reflex.db",
    telemetry_enabled=False,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

