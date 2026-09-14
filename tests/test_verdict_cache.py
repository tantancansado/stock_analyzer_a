#!/usr/bin/env python3
"""La caché del gate: menos llamadas, y la app no se vacía sin saldo.

El gate preguntaba a Claude una vez por ticker y por día. Medido en
septiembre de 2026: de 422 verificaciones, 363 eran tickers ya vistos el día
anterior — 86% de trabajo repetido sobre datos que solo cambian cada trimestre.

Y como el gate es fail-closed, quedarse sin presupuesto vaciaba
value_opportunities_filtered.csv, o sea la página principal de la app.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verdict_cache as vc


BASE = {
    'ticker': 'AAPL', 'sector': 'Technology',
    'roe': 45.2, 'profit_margin': 25.1, 'debt_to_equity': 1.5,
    'rev_growth': 8.0, 'fcf_yield_pct': 4.2,
    'current_price': 230.0, 'target_price_analyst': 260.0,
    'analyst_upside_pct': 13.0, 'pct_from_52w_high': -5.0,
    'analyst_count': 40,
}


@pytest.fixture(autouse=True)
def _aislar(tmp_path, monkeypatch):
    monkeypatch.setattr(vc, 'ESTADO', tmp_path / 'cache.json')


class TestHuella:
    """La clave es el DATO, no el ticker: si el dato cambia, se vuelve a preguntar."""

    def test_el_mismo_dato_da_la_misma_huella(self):
        assert vc.huella(BASE) == vc.huella(dict(BASE))

    @pytest.mark.parametrize('precio', [230.0, 231.5, 234.0])
    def test_el_goteo_diario_del_precio_no_invalida(self, precio):
        # Que suba un 2% no cambia si el precio es PLAUSIBLE para la empresa,
        # que es lo único que audita el gate.
        assert vc.huella(BASE) == vc.huella(dict(BASE, current_price=precio))

    def test_un_movimiento_grande_si_invalida(self):
        assert vc.huella(BASE) != vc.huella(dict(BASE, current_price=290.0))

    @pytest.mark.parametrize('campo,valor', [
        ('roe', 51.0), ('profit_margin', 12.0), ('debt_to_equity', 3.9),
        ('rev_growth', -4.0), ('fcf_yield_pct', 9.1), ('analyst_count', 12),
        ('sector', 'Energy'), ('ticker', 'MSFT'),
    ])
    def test_cambiar_un_fundamental_invalida(self, campo, valor):
        assert vc.huella(BASE) != vc.huella(dict(BASE, **{campo: valor}))

    def test_un_dato_ausente_no_revienta(self):
        assert vc.huella({'ticker': 'X'})

    def test_nan_cuenta_como_ausente(self):
        assert vc.huella(dict(BASE, roe=float('nan'))) == vc.huella({**BASE, 'roe': None})


class TestGuardarYBuscar:

    def test_sin_nada_guardado_no_hay_veredicto(self):
        assert vc.buscar(BASE) is None

    def test_un_veredicto_guardado_se_recupera(self):
        vc.guardar(BASE, True, None)
        ok, aviso, desde = vc.buscar(BASE)
        assert ok is True
        assert desde == datetime.now(timezone.utc).isoformat()[:10]

    def test_se_recupera_tambien_un_rechazo(self):
        vc.guardar(BASE, False, 'ROE imposible para el sector')
        ok, aviso, _ = vc.buscar(BASE)
        assert ok is False
        assert 'imposible' in aviso

    def test_si_cambia_el_dato_no_sirve_el_veredicto_viejo(self):
        vc.guardar(BASE, True, None)
        assert vc.buscar(dict(BASE, roe=99.0)) is None

    def test_caduca_a_los_30_dias(self):
        viejo = datetime.now(timezone.utc) - timedelta(days=vc.TTL_DIAS + 1)
        vc.guardar(BASE, True, None, ahora=viejo)
        assert vc.buscar(BASE) is None

    def test_dentro_del_plazo_sigue_valiendo(self):
        casi = datetime.now(timezone.utc) - timedelta(days=vc.TTL_DIAS - 1)
        vc.guardar(BASE, True, None, ahora=casi)
        assert vc.buscar(BASE) is not None

    def test_lo_caducado_se_purga_al_guardar(self):
        viejo = datetime.now(timezone.utc) - timedelta(days=vc.TTL_DIAS + 5)
        vc.guardar(dict(BASE, ticker='VIEJO'), True, None, ahora=viejo)
        vc.guardar(BASE, True, None)
        assert 'VIEJO' not in vc.ESTADO.read_text()

    def test_un_fichero_corrupto_no_tumba_nada(self):
        vc.ESTADO.parent.mkdir(parents=True, exist_ok=True)
        vc.ESTADO.write_text('{roto')
        assert vc.buscar(BASE) is None
        vc.guardar(BASE, True, None)          # se regenera solo
        assert vc.buscar(BASE) is not None


class TestSobreviveACI:
    """Una caché que CI no commitea no ahorra NADA.

    docs/ai_verdicts_cache.json caía en el patrón `*_cache.json` del
    .gitignore, así que se escribía en cada ejecución y se tiraba: cada run
    partía de cero, el 86% de verificaciones repetidas se seguía pagando, y la
    resistencia a quedarse sin presupuesto no existía. El mismo tropiezo que ya
    documenta claude_budget.py (allí fue por ser un dotfile).
    """

    # Ojo: el fixture _aislar de arriba reapunta vc.ESTADO a tmp_path, asi que
    # para comprobar la ruta REAL hay que releerla del fuente del modulo.
    @staticmethod
    def _ruta_real():
        import re as _re
        from pathlib import Path
        src = (Path(__file__).parent.parent / "verdict_cache.py").read_text()
        m = _re.search(r"ESTADO\s*=.*?'docs'\s*/\s*'([^']+)'", src)
        assert m, "no se pudo leer la ruta de ESTADO en verdict_cache.py"
        return m.group(1)

    def test_la_cache_no_esta_ignorada_por_git(self):
        """El fichero tiene que poder commitearse.

        `git check-ignore` devuelve 0 tanto si lo ignora una regla normal como
        si lo salva una de NEGACION, asi que el codigo de salida no vale. Lo
        que distingue los dos casos es el PATRON que casa: si empieza por `!`,
        el fichero se commitea. Y `git add --dry-run` tampoco sirve: si el
        fichero no existe en local dice "did not match any files" y el test
        pasaria en vacio.
        """
        import subprocess
        from pathlib import Path

        raiz = Path(__file__).parent.parent
        nombre = self._ruta_real()
        r = subprocess.run(
            ["git", "check-ignore", "-v", "--no-index", "--", f"docs/{nombre}"],
            cwd=raiz, capture_output=True, text=True)

        if r.returncode != 0 or not r.stdout.strip():
            return                      # ninguna regla casa: se commitea

        # formato: <fichero>:<linea>:<patron>\t<ruta>
        patron = r.stdout.split("\t")[0].split(":", 2)[2]
        assert patron.startswith("!"), (
            f"docs/{nombre} lo ignora la regla `{patron}`: CI no lo commiteara "
            f"y la cache partira de cero en cada ejecucion, sin ahorrar nada"
        )

    def test_vive_en_docs_que_es_lo_que_commitea_el_workflow(self):
        # Los workflows hacen `git add docs/*.json`, y bash no expande dotfiles.
        nombre = self._ruta_real()
        assert nombre.endswith(".json")
        assert not nombre.startswith("."), "un dotfile no lo expande bash"
