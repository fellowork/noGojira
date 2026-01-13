"""Reflex configuration for noGojira."""

import reflex as rx

config = rx.Config(
    app_name="nogojira",
    api_url="http://localhost:8484",
    backend_port=8484,
    frontend_port=8383,
    backend_host="0.0.0.0",
    db_url="sqlite:///reflex.db",
    telemetry_enabled=False,
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)

