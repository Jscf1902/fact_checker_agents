# agents/reporter.py

import logging
from datetime import datetime
import os

logger = logging.getLogger("reporter_agent")

def reporter_agent(interpretation: dict, evidence: dict = None, fact_check: dict = None):
    """
    Genera un reporte estructurado con la información obtenida - VERSIÓN SIMPLIFICADA
    """
    logger.info("Reporter: generando reporte...")
    
    # Crear directorio de reports si no existe
    os.makedirs("reports", exist_ok=True)
    
    # Generar contenido del reporte
    report_content = generate_simple_report(interpretation, evidence, fact_check)
    
    # Guardar archivo
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"reports/report_{timestamp}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info(f"Reporte guardado en {filename}")
    
    return {
        "summary": evidence.get("summary", "No hay resumen disponible") if evidence else "Sin información",
        "filename": filename,
        "timestamp": timestamp
    }

def generate_simple_report(interpretation: dict, evidence: dict, fact_check: dict) -> str:
    """Genera el contenido markdown del reporte - VERSIÓN SIMPLIFICADA"""
    
    title = interpretation.get("target_title", "Desconocido")
    intent = interpretation.get("intent", "unknown")
    
    content = f"""# 🎬 Reporte: {title}
    
**Fecha:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Intención detectada:** `{intent}`  
**Propósito:** {interpretation.get('query_purpose', 'No especificado')}

## 📊 Información Encontrada

"""
    
    if evidence:
        content += f"""
**Título:** {evidence.get('title', 'No disponible')}  
**Año:** {evidence.get('year', 'No disponible')}  
**Géneros:** {', '.join(evidence.get('genres', [])) or 'No disponibles'}  
**Director:** {evidence.get('director', 'No disponible')}  
**Rating:** {evidence.get('rating', 'No disponible')}

**📖 Sinopsis:**  
{evidence.get('summary', 'No disponible')}

"""
        
        # CAST - FORMATO SIMPLIFICADO
        cast = evidence.get("cast", [])
        if cast:
            content += f"**🎭 Reparto Principal:**\n\n"
            for actor in cast[:6]:  # Mostrar primeros 6 actores
                content += f"- {actor}\n"
            content += "\n"
        else:
            content += "**🎭 Reparto:** No disponible\n\n"
            
    else:
        content += "❌ No se encontró información.\n"
    
    if fact_check:
        status_icon = "✅" if fact_check.get('is_true') else "❌" if fact_check.get('is_true') is False else "⚠️"
        status_text = "VERDADERO" if fact_check.get('is_true') else "FALSO" if fact_check.get('is_true') is False else "INCONCLUSO"
        
        content += f"""
## 🔍 Verificación de Hechos

**Afirmación:** "{fact_check.get('claim', 'No especificada')}"  
**Resultado:** {status_icon} **{status_text}**  
**Evidencia:** {fact_check.get('evidence', 'No disponible')}
"""
    
    content += f"""
---
*Reporte generado automáticamente por el sistema de Fact Checking*
"""
    
    return content