"""Écrit le SQL qui fusionne une copie d'une base Oris (schémas `mac`, `mac_learning`)
dans la base de destination (schémas `public`, `learning`).

Le 11/11/2026, Franck ne retrouvait pas sur l'iPhone les dossiers créés la veille sur le
Mac : depuis le transport du 8 octobre, le Mac et le serveur en ligne avaient chacun leur
base, et chacune avait avancé de son côté (32 patients et 13 consultations d'un côté,
6 patients et 9 consultations de l'autre). Ce script les réunit sans rien perdre :

- une ligne absente de la destination y est ajoutée ;
- une ligne présente des deux côtés garde la version la plus récente (`updated_at`) ;
- un patient ou un correspondant créé deux fois sous le même nom (une fois de chaque côté)
  devient une seule fiche : les références de la copie sont reportées sur la fiche de la
  destination ;
- les comptes, jetons et réglages du serveur ne sont jamais touchés.

La copie doit avoir été chargée **sans contraintes** (`pg_restore --section=pre-data
--section=data`) : les identifiants s'y renomment librement. Le SQL produit s'exécute en
une seule transaction ; `--essai` le termine par ROLLBACK.

    python3 scripts/fusionner_bases.py [--essai] > fusion.sql
    psql -v ON_ERROR_STOP=1 -d oris -f fusion.sql
"""

from __future__ import annotations

import sys

# Tables fusionnées, dans l'ordre des clés étrangères. Les autres restent celles du serveur :
# organisation, comptes (mots de passe), jetons, version de schéma.
ORDRE = [
    ("learning", "model_versions"),
    ("learning", "prompt_versions"),
    ("learning", "glossary_terms"),
    ("learning", "practitioner_learning_profiles"),
    ("public", "correspondent_specialties"),
    ("public", "patients"),
    ("public", "correspondents"),
    ("public", "patient_correspondents"),
    ("public", "encounters"),
    ("public", "audio_sessions"),
    ("public", "audio_chunks"),
    ("public", "transcript_segments"),
    ("public", "encounter_marks"),
    ("public", "encounter_object_versions"),
    ("public", "clinical_facts"),
    ("public", "treatment_plans"),
    ("public", "treatment_plan_items"),
    ("public", "procedures"),
    ("public", "attachments"),
    ("public", "documents"),
    ("public", "document_versions"),
    ("public", "document_figures"),
    ("public", "document_deliveries"),
    ("public", "audit_events"),
    ("learning", "learning_events"),
    ("learning", "model_runs"),
]

# Tables de liaison sans identifiant propre : on n'ajoute que les liens dont les deux
# bouts existent dans la destination.
LIAISONS = {
    "fact_evidence_links": [("fact_id", "clinical_facts"), ("transcript_segment_id", "transcript_segments")],
    "treatment_plan_item_evidence": [("item_id", "treatment_plan_items"), ("fact_id", "clinical_facts")],
    "procedure_evidence": [("procedure_id", "procedures"), ("fact_id", "clinical_facts")],
}


def copie(schema: str) -> str:
    return "mac" if schema == "public" else "mac_learning"


def entete() -> str:
    return r"""
\set ON_ERROR_STOP on
BEGIN;

-- Colonnes communes à une table des deux côtés, dans l'ordre de la destination.
CREATE TEMP TABLE _cols AS
SELECT d.table_schema AS sch, d.table_name AS tab,
       string_agg(quote_ident(d.column_name), ', ' ORDER BY d.ordinal_position) AS liste,
       bool_or(d.column_name = 'updated_at') AS a_maj,
       bool_or(d.column_name = 'id') AS a_id
  FROM information_schema.columns d
  JOIN information_schema.columns s
    ON s.table_schema = CASE d.table_schema WHEN 'public' THEN 'mac' ELSE 'mac_learning' END
   AND s.table_name = d.table_name AND s.column_name = d.column_name
 WHERE d.table_schema IN ('public', 'learning')
 GROUP BY 1, 2;

CREATE TEMP TABLE _bilan (tab text, ajoutees int, mises_a_jour int);

-- 1. Même fiche créée des deux côtés : on garde celle de la destination.
CREATE TEMP TABLE _remap_patient AS
SELECT m.id AS mac, p.id AS cible
  FROM mac.patients m
  JOIN public.patients p
    ON upper(btrim(p.last_name)) = upper(btrim(m.last_name))
   AND lower(btrim(p.first_name)) = lower(btrim(m.first_name))
 WHERE NOT EXISTS (SELECT 1 FROM public.patients x WHERE x.id = m.id)
   AND NOT EXISTS (SELECT 1 FROM mac.patients y WHERE y.id = p.id);

CREATE TEMP TABLE _remap_corresp AS
SELECT DISTINCT ON (m.id) m.id AS mac, c.id AS cible
  FROM mac.correspondents m
  JOIN public.correspondents c
    ON upper(btrim(c.last_name)) = upper(btrim(m.last_name))
   AND lower(btrim(coalesce(c.first_name, ''))) = lower(btrim(coalesce(m.first_name, '')))
   AND c.kind = m.kind
 WHERE NOT EXISTS (SELECT 1 FROM public.correspondents x WHERE x.id = m.id)
   AND NOT EXISTS (SELECT 1 FROM mac.correspondents y WHERE y.id = c.id)
 ORDER BY m.id, c.created_at;

CREATE TEMP TABLE _remap_specialite AS
SELECT m.id AS mac, c.id AS cible FROM mac.correspondent_specialties m
  JOIN public.correspondent_specialties c USING (organization_id, label) WHERE m.id <> c.id;
CREATE TEMP TABLE _remap_modele AS
SELECT m.id AS mac, c.id AS cible FROM mac_learning.model_versions m
  JOIN learning.model_versions c USING (component, provider, model_id) WHERE m.id <> c.id;
CREATE TEMP TABLE _remap_consigne AS
SELECT m.id AS mac, c.id AS cible FROM mac_learning.prompt_versions m
  JOIN learning.prompt_versions c USING (component, version) WHERE m.id <> c.id;

-- Les références de la copie suivent (la copie n'a pas de contraintes : on renomme librement).
UPDATE mac.encounters t SET patient_id = r.cible FROM _remap_patient r WHERE t.patient_id = r.mac;
UPDATE mac.attachments t SET patient_id = r.cible FROM _remap_patient r WHERE t.patient_id = r.mac;
UPDATE mac.patient_correspondents t SET patient_id = r.cible FROM _remap_patient r WHERE t.patient_id = r.mac;
UPDATE mac.patients t SET id = r.cible FROM _remap_patient r WHERE t.id = r.mac;

UPDATE mac.patient_correspondents t SET correspondent_id = r.cible FROM _remap_corresp r WHERE t.correspondent_id = r.mac;
UPDATE mac.document_deliveries t SET correspondent_id = r.cible FROM _remap_corresp r WHERE t.correspondent_id = r.mac;
UPDATE mac.correspondents t SET id = r.cible FROM _remap_corresp r WHERE t.id = r.mac;

UPDATE mac.correspondent_specialties t SET id = r.cible FROM _remap_specialite r WHERE t.id = r.mac;
UPDATE mac_learning.model_runs t SET model_version_id = r.cible FROM _remap_modele r WHERE t.model_version_id = r.mac;
UPDATE mac_learning.model_versions t SET id = r.cible FROM _remap_modele r WHERE t.id = r.mac;
UPDATE mac_learning.model_runs t SET prompt_version_id = r.cible FROM _remap_consigne r WHERE t.prompt_version_id = r.mac;
UPDATE mac_learning.prompt_versions t SET id = r.cible FROM _remap_consigne r WHERE t.id = r.mac;

-- Un document entre d'abord sans version courante : ses versions arrivent après lui.
CREATE TEMP TABLE _version_courante AS SELECT id, current_version_id FROM mac.documents;
"""


def fusion_table(schema: str, table: str) -> str:
    src = f"{copie(schema)}.{table}"
    dst = f"{schema}.{table}"
    special_doc = table == "documents"
    return f"""
DO $$
DECLARE c record; n_ins int := 0; n_maj int := 0;
BEGIN
  SELECT * INTO c FROM _cols WHERE sch = '{schema}' AND tab = '{table}';
  IF c IS NULL THEN RETURN; END IF;
  -- La ligne la plus récente gagne, quand elle existe des deux côtés.
  IF c.a_id AND c.a_maj THEN
    EXECUTE format(
      'UPDATE {dst} t SET (%1$s) = (SELECT %2$s FROM {src} m2 WHERE m2.id = t.id)
         FROM {src} m WHERE m.id = t.id AND m.updated_at > t.updated_at',
      c.liste,
      {"replace(c.liste, 'current_version_id', 't.current_version_id')" if special_doc else "c.liste"});
    GET DIAGNOSTICS n_maj = ROW_COUNT;
  END IF;
  IF c.a_id THEN
    EXECUTE format(
      'INSERT INTO {dst} (%1$s) SELECT %2$s FROM {src} m
        WHERE NOT EXISTS (SELECT 1 FROM {dst} t WHERE t.id = m.id) ON CONFLICT DO NOTHING',
      c.liste,
      {"replace(c.liste, 'current_version_id', 'NULL::uuid')" if special_doc else "c.liste"});
    GET DIAGNOSTICS n_ins = ROW_COUNT;
  ELSE
    EXECUTE format('INSERT INTO {dst} (%1$s) SELECT %1$s FROM {src} ON CONFLICT DO NOTHING', c.liste);
    GET DIAGNOSTICS n_ins = ROW_COUNT;
  END IF;
  INSERT INTO _bilan VALUES ('{table}', n_ins, n_maj);
END $$;
"""


def fusion_liaison(table: str, bouts: list[tuple[str, str]]) -> str:
    conditions = " AND ".join(
        f"EXISTS (SELECT 1 FROM public.{cible} x WHERE x.id = m.{col})" for col, cible in bouts
    )
    return f"""
DO $$
DECLARE c record; n int;
BEGIN
  SELECT * INTO c FROM _cols WHERE sch = 'public' AND tab = '{table}';
  EXECUTE format('INSERT INTO public.{table} (%1$s) SELECT %1$s FROM mac.{table} m
                   WHERE {conditions} ON CONFLICT DO NOTHING', c.liste);
  GET DIAGNOSTICS n = ROW_COUNT;
  INSERT INTO _bilan VALUES ('{table}', n, 0);
END $$;
"""


def pied(essai: bool) -> str:
    return f"""
-- Les versions sont là : chaque document reprend sa version courante (la plus récente
-- l'emporte déjà ; un document nouveau prend celle de la copie).
UPDATE public.documents d SET current_version_id = v.current_version_id
  FROM _version_courante v
 WHERE d.id = v.id AND v.current_version_id IS NOT NULL
   AND EXISTS (SELECT 1 FROM public.document_versions x WHERE x.id = v.current_version_id)
   AND (d.current_version_id IS NULL
        OR (SELECT version FROM public.document_versions WHERE id = v.current_version_id)
         > (SELECT version FROM public.document_versions WHERE id = d.current_version_id));

SELECT tab AS "table", ajoutees AS "ajoutées", mises_a_jour AS "mises à jour"
  FROM _bilan WHERE ajoutees + mises_a_jour > 0 ORDER BY tab;
SELECT (SELECT count(*) FROM _remap_patient) AS "patients en double réunis",
       (SELECT count(*) FROM _remap_corresp) AS "correspondants en double réunis";
SELECT count(*) AS "documents sans version courante" FROM public.documents WHERE current_version_id IS NULL;

{"ROLLBACK;" if essai else "COMMIT;"}
"""


def main() -> int:
    essai = "--essai" in sys.argv
    morceaux = [entete()]
    for schema, table in ORDRE:
        morceaux.append(fusion_table(schema, table))
        if table == "clinical_facts":
            morceaux.append(fusion_liaison("fact_evidence_links", LIAISONS["fact_evidence_links"]))
        if table == "treatment_plan_items":
            morceaux.append(
                fusion_liaison("treatment_plan_item_evidence", LIAISONS["treatment_plan_item_evidence"])
            )
        if table == "procedures":
            morceaux.append(fusion_liaison("procedure_evidence", LIAISONS["procedure_evidence"]))
    morceaux.append(pied(essai))
    sys.stdout.write("".join(morceaux))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
