# Suite de Verificación DSVH

> **Paper companero**: [LOUST-PRO/deterministic-sovereign-rag](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
> **Operador**: David Mireles — ORCID [0009-0008-4374-2254](https://orcid.org/0009-0008-4374-2254)
> **Licencia**: Apache-2.0
> **Idiomas**: [English (README.md)](./README.md) · Español (este archivo)

Este repositorio empaqueta la **suite de verificación** que respalda
la formalización del paper companero
[*Deterministic Sovereign RAG via Signed-Hash Projection*](https://github.com/LOUST-PRO/deterministic-sovereign-rag)
(Recuperación-Augmentada Determinista y Soberana vía Proyección por
Hash Firmado). El paper es el subconjunto reducido listo para
someterse a arXiv; este repositorio contiene las **verificaciones
ejecutables** — los vectores de prueba deterministas, las pruebas
de round-trip sobre FNV-1a, los volcados de trazas de proyección
esférica L2, los archivos golden del backoff Bayesiano, y el
auditor de deriva entre las matemáticas y el runtime.

Para ver la arquitectura completa y el operator-stack usado en
producción, consultá [loust.pro/dsvh](https://loust.pro/dsvh).

## Estado

Este repositorio se publica como un **artefacto de procedencia de
publicación**: registra la disciplina de frontera-IP aplicada a la
superficie de verificación del paper companero. El contrato de
frontera-IP (lista vinculante de patrones prohibidos, rutas
internas del operador, e identificadores del tooling) está
documentado en
[`verification/anonymization-lexicon.md`](https://github.com/LOUST-PRO/deterministic-sovereign-rag/blob/main/verification/anonymization-lexicon.md)
del repositorio del paper companero.

La frontera se enforce del lado de la publicación mediante un hook
pre-publish guard que se dispara en cada Write/Edit sobre rutas de
public staging, y mediante el barrido del public-surface curator
aplicado antes de publicar.

## Qué contiene este repositorio

```
dsvh-verification-suite/
├── README.md                       # este archivo (EN)
├── README.es.md                    # este archivo (ES)
├── LICENSE                         # Apache-2.0
├── MANIFEST.md                     # procedencia de publicación + items abiertos
├── TRACEABILITY.md                 # mapa bidireccional paper ↔ vectores ↔ auditor
├── MISSING-TESTS.md                # brechas propuestas (sin implementar)
├── CITATION.cff                    # metadatos ORCID + Apache-2.0
├── .gitignore                      # defensivo (frontera-IP + secretos)
├── scripts/
│   └── zenodo_oauth_test.py        # test E2E de autenticación con Zenodo
├── tests/                          # 412 vectores/eventos en 4 archivos JSON
│   ├── README.md                   # contrato JSON, esquema, qué cubre y qué no
│   ├── fnv1a_64_vectors.json       # 24 vectores (paper §3.1)
│   ├── l2_projection_golden.json   # 12 vectores (paper §3.3)
│   ├── bayesian_backoff_golden.json # 16 vectores (paper §8)
│   └── zero_token_keepalive_trace.json  # 6 trazas / 360 eventos (paper §9)
├── auditors/
│   ├── README.md                   # qué verifica, exit codes, tolerancias
│   └── math_runtime_drift.py       # auditor de deriva matemática ↔ traza (stdlib)
└── .github/
    ├── DISCUSSIONS.md              # especificación de categorías de Discussions
    └── PROJECTS-arxiv-submission.md  # especificación del board de submission a arXiv
```

Las 412 entradas en `tests/` están ancladas al paper companero
vía el campo `paper_section` declarado en cada JSON, y se
verifican con `python3 auditors/math_runtime_drift.py` desde la
raíz del suite.

## Qué NO contiene este repositorio

Este repositorio es la **superficie pública de verificación** del
paper. NO incluye:

- El runtime de producción (Jaccard, paths AVX2, mitigaciones de
  caché fría). Ver [loust.pro/dsvh](https://loust.pro/dsvh) para
  el operator-stack.
- Los componentes propietarios referidos como "spec-aligned reduced
  alternatives" en el paper.
- Memorandos internos de estrategia, notas de contrainteligencia,
  o diagnósticos de persona.
- Credenciales ORCID, claves de firma, o tokens del operador.

La frontera se enforce mediante `anonymization-lexicon.md` en el
repositorio del paper companero (vinculante) y mediante el hook
pre-publish guard del operador del lado de la publicación.

## Cómo contribuir / Endorsement

Si tenés un **endorsement de arXiv** en `cs.IR` o `cs.DS` y estás
dispuesto a **endosar este submission** (o a co-revisar un draft),
abrí un GitHub Discussion en la
[categoría Endorsement](./.github/DISCUSSIONS.md#endorsement)
(revisor-privado-a-autor) o escribinos a **research@loust.pro**.

Para preguntas metodológicas, auditorías de reproducibilidad, o
reportar discrepancias entre las matemáticas del paper y los
vectores de verificación, abrí un GitHub Discussion en la
[categoría Q&A](./.github/DISCUSSIONS.md#qa).

## Citación

Si usás esta suite de verificación o el paper companero, citá
ambos:

```bibtex
@misc{mireles2026deterministic,
  author       = {Mireles, David},
  title        = {Deterministic Sovereign RAG via Signed-Hash Projection:
                  An Operator-Stack Formalization of FNV-1a 64-bit +
                  L2 Spherical Projection at D=128 for Reproducible
                  Retrieval on Sovereign Cloud Infrastructure},
  year         = {2026},
  howpublished = {arXiv preprint},
  orcid        = {0009-0008-4374-2254},
}
```

El `CITATION.cff` completo se incluye desde v0.1.0 con los
metadatos ORCID + Apache-2.0.

## Licencia

Apache License 2.0. Ver [`LICENSE`](./LICENSE) para el texto
completo y la atribución de terceros.
