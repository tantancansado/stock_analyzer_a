"""Interés abierto NaN: ni se trata como cero ni acaba en el JSON."""
import json
import options_flow_detector as o


def test_sin_nan_limpia_anidados():
    out = o._sin_nan({'a': float('nan'), 'b': [1.0, {'c': float('inf')}]})
    assert out == {'a': None, 'b': [1.0, {'c': None}]}
    json.dumps(out, allow_nan=False)


def test_los_numeros_normales_no_se_tocan():
    assert o._sin_nan({'x': 1.5, 'y': 0, 's': 'NaN'}) == {'x': 1.5, 'y': 0, 's': 'NaN'}


def test_el_detector_descarta_contratos_sin_interes_abierto():
    from pathlib import Path
    src = (Path(o.__file__)).read_text()
    assert src.count('if oi is None or oi != oi:') == 2, 'calls y puts'
