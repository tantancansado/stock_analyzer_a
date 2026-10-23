"""Cabecera Authorization para Supabase según el tipo de clave.

Las claves antiguas (anon, service_role) son JWT y van también como
`Authorization: Bearer`. Las nuevas (`sb_secret_…`, `sb_publishable_…`) no son
JWT: solo viajan en `apikey`, y mandarlas de portador no vale. Los scripts
mandaban siempre las dos, así que cambiar de tipo de clave los rompía.
"""
from __future__ import annotations


def bearer(key: str) -> dict:
    """{'Authorization': 'Bearer …'} si la clave es un JWT; {} si es una clave nueva."""
    return {'Authorization': f'Bearer {key}'} if str(key or '').startswith('eyJ') else {}
