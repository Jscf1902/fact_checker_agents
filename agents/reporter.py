# agents/reporter.py

import logging
import os
import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reporter_agent")


# ----------------------------------------------------
#   Construcción segura del Markdown
# ----------------------------------------------------
def build_markdown(
    interpretation: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    fact_check: Optional[Dict[str, Any]],
    reference_doc: Optional[str] = None
) -> str:

    # Protección: asegurar que interpretation sea un dict
    if not isinstance(interpretation, dict):
        logger.warning(f"[Reporter] Interpretación NO es dict. Valor recibido: {interpretation}")
        interpretation = {"intent": str(interpretation), "entities": {}}

    lines = []
    lines.append(f"# Reporte generado - {datetime.datetime.utcnow().isoformat()} UTC\n")

    # ----------------------
    # INTERPRETACIÓN
    # ----------------------
    lines.append("## Interpretación de la consulta\n")
    lines.append(f"- **Intención:** {interpretation.get('intent')}\n")

    entities = interpretation.get("entities", {})
    for k, v in entities.items():
        lines.append(f"- **{k}:** {v}\n")
    lines.append("\n")

    # ----------------------
    # EVIDENCIA WEB
    # ----------------------
    lines.append("## Evidencia (Web Search / Scraper)\n")
    if evidence:
        lines.append(f"- **Fuente:** {evidence.get('source', 'tmdb')}\n")
        lines.append(f"- **URL:** {evidence.get('url')}\n")
        if evidence.get("title"):
            lines.append(f"- **Título:** {evidence.get('title')}\n")
        if evidence.get("year"):
            lines.append(f"- **Año:** {evidence.get('year')}\n")
        if evidence.get("genres"):
            lines.append(f"- **Géneros:** {', '.join(evidence.get('genres'))}\n")
        if evidence.get("score"):
            lines.append(f"- **Puntuación usuarios:** {evidence.get('score')}/100\n")

        if evidence.get("overview"):
            lines.append("\n### Resumen / Overview\n")
            lines.append(evidence["overview"] + "\n")

        # Reparto
        cast = evidence.get("cast", [])
        if cast:
            lines.append("\n### Reparto (Top)\n")
            for c in cast[:10]:
                actor = c.get("actor", "desconocido")
                character = c.get("character", "—")
                lines.append(f"- {actor} — {character}\n")
    else:
        lines.append("No se encontró evidencia web.\n")

    # ----------------------
    # FACT CHECKING
    # ----------------------
    lines.append("\n## Resultado del fact-check\n")
    if fact_check:
        result = fact_check.get("is_true")
        if result is True:
            status = "VERDADERO"
        elif result is False:
            status = "FALSO"
        else:
            status = "INSUFICIENTE EVIDENCIA"

        lines.append(f"- **Estado:** {status}\n")
        lines.append(f"- **Confianza:** {fact_check.get('confidence', 0.0)}\n")
        lines.append(f"- **Evidencia:** {fact_check.get('evidence')}\n")
    else:
        lines.append("No se realizó fact-check.\n")

    # ----------------------
    # REFERENCIA ADICIONAL
    # ----------------------
    if reference_doc:
        lines.append("\n---\n")
        lines.append(f"Referencia: {reference_doc}\n")

    return "\n".join(lines)


# ----------------------------------------------------
#   AGENTE REPORTER
# ----------------------------------------------------
def reporter_agent(
    interpretation: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    fact_check: Optional[Dict[str, Any]],
    reference_doc: Optional[str] = None
) -> Dict[str, Any]:

    logger.info("Reporter: generando reporte...")

    # Normalización: asegurar dict
    if not isinstance(interpretation, dict):
        logger.warning("[Reporter] Interpretación incorrecta. Corrigiendo...")
        interpretation = {"intent": str(interpretation), "entities": {}}

    # Construcción del texto
    md = build_markdown(interpretation, evidence, fact_check, reference_doc)

    out = {
        "markdown": md,
        "path": None,
        "summary": None
    }

    # Resumen para la respuesta natural
    if evidence and evidence.get("overview"):
        text = evidence["overview"]
        out["summary"] = text[:300] + ("..." if len(text) > 300 else "")
    elif fact_check:
        out["summary"] = fact_check.get("evidence")
    else:
        out["summary"] = "No hay resumen disponible."

    # ----------------------
    # Guardar archivo
    # ----------------------
    try:
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"reports/report_{timestamp}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)

        out["path"] = os.path.abspath(filename)
        logger.info(f"Reporte guardado en {out['path']}")

    except Exception as e:
        logger.exception("No se pudo guardar el reporte")
        out["path"] = None

    return out


# ----------------------------------------------------
# PRUEBA RÁPIDA
# ----------------------------------------------------
if __name__ == "__main__":
    fake_interp = {
        "intent": "fact_check",
        "entities": {
            "title": "breaking bad",
            "person": "bryan cranston",
            "claim": "Verifica si Bryan Cranston ganó un Emmy"
        }
    }

    fake_ev = {
        "title": "Breaking Bad",
        "overview": "Resumen de prueba",
        "cast": [{"actor": "Bryan Cranston", "character": "Walter White"}],
        "url": "https://example"
    }

    fake_fc = {
        "claim": "Verifica si Bryan Cranston ganó un Emmy",
        "is_true": True,
        "evidence": "Bryan Cranston ganó Emmys",
        "confidence": 0.9
    }

    print(reporter_agent(fake_interp, fake_ev, fake_fc))
# agents/reporter.py

import logging
import os
import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reporter_agent")


# ----------------------------------------------------
#   Construcción segura del Markdown
# ----------------------------------------------------
def build_markdown(
    interpretation: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    fact_check: Optional[Dict[str, Any]],
    reference_doc: Optional[str] = None
) -> str:

    # Protección: asegurar que interpretation sea un dict
    if not isinstance(interpretation, dict):
        logger.warning(f"[Reporter] Interpretación NO es dict. Valor recibido: {interpretation}")
        interpretation = {"intent": str(interpretation), "entities": {}}

    lines = []
    lines.append(f"# Reporte generado - {datetime.datetime.utcnow().isoformat()} UTC\n")

    # ----------------------
    # INTERPRETACIÓN
    # ----------------------
    lines.append("## Interpretación de la consulta\n")
    lines.append(f"- **Intención:** {interpretation.get('intent')}\n")

    entities = interpretation.get("entities", {})
    for k, v in entities.items():
        lines.append(f"- **{k}:** {v}\n")
    lines.append("\n")

    # ----------------------
    # EVIDENCIA WEB
    # ----------------------
    lines.append("## Evidencia (Web Search / Scraper)\n")
    if evidence:
        lines.append(f"- **Fuente:** {evidence.get('source', 'tmdb')}\n")
        lines.append(f"- **URL:** {evidence.get('url')}\n")
        if evidence.get("title"):
            lines.append(f"- **Título:** {evidence.get('title')}\n")
        if evidence.get("year"):
            lines.append(f"- **Año:** {evidence.get('year')}\n")
        if evidence.get("genres"):
            lines.append(f"- **Géneros:** {', '.join(evidence.get('genres'))}\n")
        if evidence.get("score"):
            lines.append(f"- **Puntuación usuarios:** {evidence.get('score')}/100\n")

        if evidence.get("overview"):
            lines.append("\n### Resumen / Overview\n")
            lines.append(evidence["overview"] + "\n")

        # Reparto
        cast = evidence.get("cast", [])
        if cast:
            lines.append("\n### Reparto (Top)\n")
            for c in cast[:10]:
                actor = c.get("actor", "desconocido")
                character = c.get("character", "—")
                lines.append(f"- {actor} — {character}\n")
    else:
        lines.append("No se encontró evidencia web.\n")

    # ----------------------
    # FACT CHECKING
    # ----------------------
    lines.append("\n## Resultado del fact-check\n")
    if fact_check:
        result = fact_check.get("is_true")
        if result is True:
            status = "VERDADERO"
        elif result is False:
            status = "FALSO"
        else:
            status = "INSUFICIENTE EVIDENCIA"

        lines.append(f"- **Estado:** {status}\n")
        lines.append(f"- **Confianza:** {fact_check.get('confidence', 0.0)}\n")
        lines.append(f"- **Evidencia:** {fact_check.get('evidence')}\n")
    else:
        lines.append("No se realizó fact-check.\n")

    # ----------------------
    # REFERENCIA ADICIONAL
    # ----------------------
    if reference_doc:
        lines.append("\n---\n")
        lines.append(f"Referencia: {reference_doc}\n")

    return "\n".join(lines)


# ----------------------------------------------------
#   AGENTE REPORTER
# ----------------------------------------------------
def reporter_agent(
    interpretation: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    fact_check: Optional[Dict[str, Any]],
    reference_doc: Optional[str] = None
) -> Dict[str, Any]:

    logger.info("Reporter: generando reporte...")

    # Normalización: asegurar dict
    if not isinstance(interpretation, dict):
        logger.warning("[Reporter] Interpretación incorrecta. Corrigiendo...")
        interpretation = {"intent": str(interpretation), "entities": {}}

    # Construcción del texto
    md = build_markdown(interpretation, evidence, fact_check, reference_doc)

    out = {
        "markdown": md,
        "path": None,
        "summary": None
    }

    # Resumen para la respuesta natural
    if evidence and evidence.get("overview"):
        text = evidence["overview"]
        out["summary"] = text[:300] + ("..." if len(text) > 300 else "")
    elif fact_check:
        out["summary"] = fact_check.get("evidence")
    else:
        out["summary"] = "No hay resumen disponible."

    # ----------------------
    # Guardar archivo
    # ----------------------
    try:
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"reports/report_{timestamp}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)

        out["path"] = os.path.abspath(filename)
        logger.info(f"Reporte guardado en {out['path']}")

    except Exception as e:
        logger.exception("No se pudo guardar el reporte")
        out["path"] = None

    return out


# ----------------------------------------------------
# PRUEBA RÁPIDA
# ----------------------------------------------------
if __name__ == "__main__":
    fake_interp = {
        "intent": "fact_check",
        "entities": {
            "title": "breaking bad",
            "person": "bryan cranston",
            "claim": "Verifica si Bryan Cranston ganó un Emmy"
        }
    }

    fake_ev = {
        "title": "Breaking Bad",
        "overview": "Resumen de prueba",
        "cast": [{"actor": "Bryan Cranston", "character": "Walter White"}],
        "url": "https://example"
    }

    fake_fc = {
        "claim": "Verifica si Bryan Cranston ganó un Emmy",
        "is_true": True,
        "evidence": "Bryan Cranston ganó Emmys",
        "confidence": 0.9
    }

    print(reporter_agent(fake_interp, fake_ev, fake_fc))
