# agents/reporter.py

import logging
from datetime import datetime
import os

logger = logging.getLogger("reporter_agent")


def reporter_agent(interpretation: dict, evidence: dict = None, fact_check: dict = None):
    """
    Genera un reporte estructurado con validaciones más sólidas.
    Mantiene tu estructura pero mejora calidad, consistencia y robustez.
    """
    logger.info("Reporter: generando reporte...")

    # Crear carpeta de reportes si no existe
    os.makedirs("reports", exist_ok=True)

    # Crear contenido
    report_content = generate_simple_report(interpretation, evidence, fact_check)

    # Guardar archivo en .md
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"reports/report_{timestamp}.md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"Reporte guardado en {filename}")

    # Resumen seguro
    summary = None
    if evidence:
        summary = evidence.get("summary")
        if not summary:
            summary = f"Información general disponible sobre: {evidence.get('title', 'desconocido')}"
    else:
        summary = "Sin información."

    return {
        "summary": summary,
        "filename": filename,
        "timestamp": timestamp
    }


def generate_simple_report(interpretation: dict, evidence: dict, fact_check: dict) -> str:
    """Genera contenido del reporte MD con validaciones adicionales."""

    # Interpretación segura
    title = interpretation.get("target_title") or "Título no identificado"
    intent = interpretation.get("intent") or "unknown"
    purpose = interpretation.get("query_purpose") or "No especificado"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    content = f"""# 🎬 Reporte: {title}

**Fecha:** {now}  
**Intención detectada:** `{intent}`  
**Propósito:** {purpose}

## 📊 Información Encontrada

"""

    # ------------------------------------------------------
    # INFORMACIÓN – Más validaciones
    # ------------------------------------------------------
    if evidence:
        ev_title = evidence.get("title", "No disponible")
        ev_year = evidence.get("year", "No disponible")
        ev_genres = evidence.get("genres") or []
        ev_director = evidence.get("director", "No disponible")
        ev_rating = evidence.get("rating", "No disponible")
        ev_summary = evidence.get("summary", "No disponible")

        genres_formatted = ", ".join(ev_genres) if ev_genres else "No disponibles"

        content += f"""
**Título:** {ev_title}  
**Año:** {ev_year}  
**Géneros:** {genres_formatted}  
**Director:** {ev_director}  
**Rating:** {ev_rating}

**📖 Sinopsis:**  
{ev_summary}

"""

        # CAST – con validaciones adicionales
        cast = evidence.get("cast") or []

        if cast:
            content += f"**🎭 Reparto Principal:**\n\n"
            for actor in cast[:6]:
                content += f"- {actor}\n"
            content += "\n"
        else:
            content += "**🎭 Reparto:** No disponible\n\n"

    else:
        content += "❌ No se encontró información.\n\n"

    # ------------------------------------------------------
    # FACT-CHECKING (si existe)
    # ------------------------------------------------------
    if fact_check:
        fc_claim = fact_check.get("claim", "No especificada")
        fc_truth = fact_check.get("is_true")
        fc_evidence = fact_check.get("evidence", "No disponible")

        status_icon = (
            "✅" if fc_truth is True else
            "❌" if fc_truth is False else
            "⚠️"
        )

        status_text = (
            "VERDADERO" if fc_truth is True else
            "FALSO" if fc_truth is False else
            "INCONCLUSO"
        )

        content += f"""
## 🔍 Verificación de Hechos

**Afirmación:** "{fc_claim}"  
**Resultado:** {status_icon} **{status_text}**  
**Evidencia:** {fc_evidence}

"""

    else:
        # No agregar bloque vacío, solo una línea informativa suave
        content += "## 🔍 Verificación de Hechos\n\nNo se realizó verificación para esta consulta.\n\n"

    # ------------------------------------------------------
    # PIE
    # ------------------------------------------------------
    content += """
---
*Reporte generado automáticamente por el sistema de Fact Checking*
"""

    return content
