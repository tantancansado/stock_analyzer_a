#!/usr/bin/env python3
"""El plan de salida de un LEAPS sale del precio objetivo, no de la ganancia.

El usuario lo desmintió el 11-ago-2026 y está en CLAUDE.md: no existe un
«objetivo del 5-10%», se vende cuando la empresa vale lo que vale, y la
calidad del negocio modula si se aguanta hasta el objetivo completo o se sale
antes. Nunca por porcentaje ganado ni por nivel técnico.

El 22-sep-2026, NUEVE de los once LEAPS publicados remataban el take-profit
con «o la opción duplica su valor», y UNH además con «(recupera zona de
máximos)». No era un fallo del modelo: el prompt le pedía literalmente
«precio/ganancia concreta».

Dos defensas: el prompt lo prohíbe, y esto lo comprueba — porque la primera
depende de que un modelo obedezca.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from leaps_analyzer import _SALIDA_PROHIBIDA, _salida_por_valoracion


class TestSeQuitaLaSalidaPorGanancia:

    def test_el_caso_de_amzn(self):
        r = _salida_por_valoracion(
            'Tomar beneficios parciales si AMZN se acerca a $329 (target analistas) '
            'o la opción duplica su valor.')
        assert '$329' in r and 'duplica' not in r

    def test_tambien_cuando_van_unidas_por_y(self):
        r = _salida_por_valoracion(
            'Considera recoger beneficios si CVX supera el target de analistas '
            '($222.67) y la opción duplica el rendimiento de la acción.')
        assert '$222.67' in r and 'duplica' not in r

    def test_el_porcentaje_ganado_tampoco(self):
        r = _salida_por_valoracion(
            'Vender si la acción se acerca a $378 (target analistas) o la opción '
            'sube +50% antes de vencimiento.')
        assert '$378' in r and '+50%' not in r

    def test_si_solo_hay_nivel_tecnico_no_se_inventa_un_objetivo(self):
        r = _salida_por_valoracion(
            'Tomar beneficios parciales si la acción se acerca a $450-460 '
            '(recupera zona de máximos) o la opción duplica su valor.')
        assert 'Sin objetivo de valoración' in r

    def test_un_plan_correcto_no_se_toca(self):
        bueno = ('Tomar beneficios si la acción se acerca a $250 (target analistas), '
                 'donde la opción ya captura gran parte del upside.')
        assert _salida_por_valoracion(bueno) == bueno

    def test_vacio_no_revienta(self):
        assert _salida_por_valoracion('') == ''
        assert _salida_por_valoracion(None) is None


class TestElPromptLoProhibe:

    def test_el_prompt_dice_que_no_se_sale_por_porcentaje(self):
        import leaps_analyzer as la
        fuente = la.add_ai_narrative.__doc__ or ''
        import inspect
        cuerpo = inspect.getsource(la.add_ai_narrative)
        assert 'PROHIBIDO' in cuerpo and 'nivel técnico' in cuerpo, (
            'sin la prohibición en el prompt, el filtro de salida trabaja solo y '
            'se pierde la mitad de las frases'
        )


class TestLoPublicado:

    def test_ningun_leaps_publicado_sale_por_ganancia(self):
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta = os.path.join(raiz, 'docs', 'leaps_opportunities.json')
        if not os.path.exists(ruta):
            pytest.skip('sin LEAPS publicados')
        with open(ruta) as fh:
            d = json.load(fh)
        culpables = []
        for o in d.get('opportunities', []):
            tp = (o.get('exit_plan') or {}).get('take_profit', '')
            m = _SALIDA_PROHIBIDA.search(tp or '')
            if m:
                culpables.append(f"{o.get('ticker')}: «{m.group(0)}»")
        assert not culpables, (
            f'Planes de salida por ganancia o por gráfico: {culpables}')


class TestElEscenarioPrudenteEsPrudente:
    """Un «escenario prudente» por encima del consenso es el caso alcista con
    otra etiqueta.

    `target_prudente` es el menor de DCF y P/E. Al retirar los DCF construidos
    sobre un FCF que se comía el capex (23-sep-2026), a AMZN le quedó solo su
    P/E —493 $ con la acción a 255— y a MSFT el suyo —632 con la acción a
    498—. El bloque seguía publicando «si la acción llega a 493, la opción
    rinde…» bajo el rótulo de escenario prudente.
    """

    def test_no_se_publica_un_escenario_por_encima_del_consenso(self):
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'docs', 'leaps_opportunities.json')
        if not os.path.exists(ruta):
            pytest.skip('sin LEAPS publicados')
        with open(ruta) as fh:
            d = json.load(fh)
        culpables = []
        for o in d.get('opportunities', []):
            esc = (o.get('profit_at_target') or {}).get('escenario_prudente')
            up = o.get('analyst_upside_pct')
            spot = o.get('spot')
            if not esc or up is None or not spot:
                continue
            consenso = spot * (1 + up / 100)
            if esc['target_price'] >= consenso:
                culpables.append(
                    f"{o.get('ticker')}: prudente {esc['target_price']} >= consenso {consenso:.0f}")
        assert not culpables, f'Escenarios «prudentes» más optimistas que el analista: {culpables}'

    def test_el_codigo_lo_impide(self):
        import inspect
        import leaps_analyzer as la
        cuerpo = inspect.getsource(la)
        assert 'sin_escenario_prudente' in cuerpo
