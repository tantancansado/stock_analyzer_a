#!/usr/bin/env python3
"""Shared runtime/config helpers for ticker_api.py."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from jwt import PyJWKClient


def env_flag(name: str, default: bool = False, environ: Optional[Mapping[str, str]] = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_production_env(environ: Optional[Mapping[str, str]] = None) -> bool:
    env = environ if environ is not None else os.environ
    return env.get("FLASK_ENV") == "production" or bool(env.get("RAILWAY_ENVIRONMENT"))


def build_allowed_emails(environ: Optional[Mapping[str, str]] = None) -> frozenset[str]:
    """Lista blanca de emails para el self-signup de Supabase Auth.

    Sin esto, cualquiera que se registre desde el formulario de la app obtiene
    un JWT de Supabase válido, y el resto del middleware (_check_auth) solo
    comprueba que el token esté FIRMADO por Supabase — no de QUIÉN es. Un
    self-signup abierto sin esta lista deja entrar a cualquiera que encuentre
    la URL a todos los endpoints no públicos.

    Vacía (var sin configurar) = comportamiento anterior, sin restringir por
    email — igual que el resto de gates opcionales de este módulo (JWKS,
    secret): no forzar un candado a medio configurar en producción por error.
    """
    env = environ if environ is not None else os.environ
    raw = env.get("ALLOWED_EMAILS", "").strip()
    if not raw:
        return frozenset()
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def build_cors_origins(environ: Optional[Mapping[str, str]] = None) -> list[str]:
    env = environ if environ is not None else os.environ
    configured = env.get("ALLOWED_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    else:
        origins = ["https://tantancansado.github.io"]

    if not is_production_env(env):
        for origin in (
            "http://localhost:5173",
            "http://localhost:4173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ):
            if origin not in origins:
                origins.append(origin)
    return origins


@dataclass(frozen=True)
class ApiRuntimeConfig:
    is_production: bool
    default_hourly_limit: str
    default_daily_limit: str
    rate_limit_storage_uri: str
    auth_bypass_enabled: bool
    require_supabase_auth: bool
    public_paths: Tuple[str, ...]
    cors_origins: list[str]
    supabase_url: str
    jwks_client: Optional[PyJWKClient]
    allowed_emails: frozenset[str]


def load_runtime_config(environ: Optional[Mapping[str, str]] = None) -> ApiRuntimeConfig:
    env = environ if environ is not None else os.environ
    is_production = is_production_env(env)
    supabase_url = env.get("SUPABASE_URL", "")
    return ApiRuntimeConfig(
        is_production=is_production,
        default_hourly_limit=env.get("MAX_REQUESTS_PER_HOUR", "100"),
        default_daily_limit=env.get("MAX_REQUESTS_PER_DAY", "500"),
        rate_limit_storage_uri=env.get("RATE_LIMIT_STORAGE_URI", "memory://"),
        auth_bypass_enabled=env_flag("AUTH_BYPASS", default=not is_production, environ=env),
        require_supabase_auth=env_flag("REQUIRE_SUPABASE_AUTH", default=is_production, environ=env),
        public_paths=("/", "/api/health"),
        cors_origins=build_cors_origins(env),
        supabase_url=supabase_url,
        jwks_client=(
            PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json", cache_jwk_set=True)
            if supabase_url else None
        ),
        allowed_emails=build_allowed_emails(env),
    )
