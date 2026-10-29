"""Las claves nuevas de Supabase no son JWT: no van de portador."""
from supabase_auth import bearer


def test_clave_jwt_antigua_va_de_portador():
    assert bearer('eyJhbGciOi.x.y') == {'Authorization': 'Bearer eyJhbGciOi.x.y'}


def test_clave_nueva_no_va_de_portador():
    assert bearer('sb_secret_abc') == {}
    assert bearer('') == {} and bearer(None) == {}


def test_ningun_script_manda_la_clave_de_portador_a_pelo():
    from pathlib import Path
    raiz = Path(__file__).resolve().parents[1]
    for f in ('portfolio_artifacts.py', 'check_alerts.py',
              'supabase_positions.py', 'ticker_api.py'):
        src = (raiz / f).read_text()
        assert "from supabase_auth import bearer" in src, f
        for var in ('SERVICE_KEY', 'SUPABASE_KEY', 'service_key'):
            assert f"'Authorization': f'Bearer {{{var}}}'" not in src, (f, var)
