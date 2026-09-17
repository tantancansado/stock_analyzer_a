

class TestLasTresListasNoSeArrastran:
    """Momentum murió con un error cosmético y se llevó a VALUE por delante.

    17-sep-2026: `add_entry_exit_prices()` (momentum) lanzó un TypeError al
    imprimir su top 10 y abortó el proceso entero. VALUE US y VALUE EU nunca
    llegaron a ejecutarse, así que `value_opportunities.csv` se publicó SIN
    `entry_price`, SIN `stop_loss` y SIN `rr_operativo` — justo lo que se mira
    para comprar.

    Y no se notó porque las columnas no estaban: no había un hueco visible en
    la tabla, había una lista de columnas más corta.
    """

    def test_un_fallo_en_una_lista_no_tumba_las_otras(self, tmp_path, monkeypatch):
        import add_entry_exit_to_opportunities as m
        llamadas = []

        def _momentum_roto(*a, **k):
            raise TypeError("Column 'risk_reward' has dtype object")

        monkeypatch.setattr(m, 'add_entry_exit_prices', _momentum_roto)
        monkeypatch.setattr(m, '_enrich_csv_with_entry_exit', lambda f: llamadas.append(f))
        monkeypatch.setattr(m.Path, 'exists', lambda self: True)
        monkeypatch.setattr(m.pd, 'read_csv', lambda *a, **k: m.pd.DataFrame({'ticker': ['X']}))

        fallos = m.add_entry_exit_all()
        assert fallos == 1, 'momentum falla y se cuenta'
        assert len(llamadas) == 2, 'VALUE US y VALUE EU tienen que haberse ejecutado igual'

    def test_el_proceso_avisa_de_que_algo_se_quedo_sin_precios(self, tmp_path, monkeypatch):
        """Si no devuelve nada distinto, el paso del pipeline da luz verde."""
        import add_entry_exit_to_opportunities as m
        monkeypatch.setattr(m, 'add_entry_exit_prices', lambda *a, **k: None)
        monkeypatch.setattr(m.Path, 'exists', lambda self: False)
        assert m.add_entry_exit_all() == 0
