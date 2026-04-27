-- ─────────────────────────────────────────────────────────────────────────────
-- user_artifacts: per-user generated outputs (strategies, earnings theses, options)
--
-- Reemplaza/complementa los JSONs estáticos en docs/ para datos que dependen
-- de la cartera real de cada usuario (que cambia cuando edita posiciones).
--
-- Ejecutar en Supabase Dashboard > SQL Editor.
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.user_artifacts (
    id          uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid           NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    kind        text           NOT NULL CHECK (kind IN (
                                  'portfolio_strategies',
                                  'earnings_theses',
                                  'earnings_options'
                              )),
    payload     jsonb          NOT NULL,
    source      text           NOT NULL DEFAULT 'pipeline'
                                CHECK (source IN ('pipeline', 'on_demand')),
    updated_at  timestamptz    NOT NULL DEFAULT now(),
    created_at  timestamptz    NOT NULL DEFAULT now(),
    -- Solo una fila viva por (user, kind). Upsert sobrescribe.
    UNIQUE (user_id, kind)
);

CREATE INDEX IF NOT EXISTS user_artifacts_user_kind_idx
    ON public.user_artifacts (user_id, kind);

CREATE INDEX IF NOT EXISTS user_artifacts_updated_idx
    ON public.user_artifacts (updated_at DESC);

-- ── RLS: cada usuario solo ve los suyos ──────────────────────────────────────
ALTER TABLE public.user_artifacts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_artifacts_select_own ON public.user_artifacts;
CREATE POLICY user_artifacts_select_own ON public.user_artifacts
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS user_artifacts_insert_own ON public.user_artifacts;
CREATE POLICY user_artifacts_insert_own ON public.user_artifacts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS user_artifacts_update_own ON public.user_artifacts;
CREATE POLICY user_artifacts_update_own ON public.user_artifacts
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS user_artifacts_delete_own ON public.user_artifacts;
CREATE POLICY user_artifacts_delete_own ON public.user_artifacts
    FOR DELETE USING (auth.uid() = user_id);

-- El service-role (que usa el pipeline + Flask) salta RLS por defecto.

-- ── Helper view: latest_artifacts por user ──────────────────────────────────
-- Útil para inspeccionar desde el dashboard
CREATE OR REPLACE VIEW public.latest_artifacts_summary AS
SELECT
    user_id,
    kind,
    source,
    updated_at,
    jsonb_array_length(COALESCE(payload->'snapshots', payload->'theses', payload->'strategies', '[]'::jsonb)) AS items_estimated,
    pg_column_size(payload) AS payload_bytes
FROM public.user_artifacts;
