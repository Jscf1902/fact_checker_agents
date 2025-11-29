# agents/interpreter.py

import logging
import re

logger = logging.getLogger("interpreter_agent")

def interpreter_agent(query: str):
    """
    Interpretación basada en reglas para cuando falla el LLM
    """
    logger.info(f"Interpretando consulta: {query}")
    
    query_lower = query.lower()
    
    # Mejor detección de títulos en consultas comunes
    title_patterns = [
        r"(?:sobre|acerca de|de|la pel[ií]cula|el libro|la serie)[\s']*([^\.\?\!,]+)",
        r"(?:busca|buscar|encuentra|encontrar)[\s']*([^\.\?\!,]+)",
        r"(?:analiza|analizar)[\s']*([^\.\?\!,]+)",
        r"(?:informaci[óo]n sobre)[\s']*([^\.\?\!,]+)"
    ]
    
    title = None
    for pattern in title_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            potential_title = match.group(1).strip()
            # Filtrar palabras comunes que no son títulos
            if len(potential_title) > 3 and not potential_title in ["información", "datos", "algo"]:
                title = potential_title.title()
                break
    
    # Intentar extraer el título después de patrones específicos
    if not title:
        # Patrón simple: última parte de la consulta como título
        words = query.split()
        if len(words) > 2:
            title = " ".join(words[-2:])  # Últimas 2 palabras como título
    
    # Determinar intención
    if any(word in query_lower for word in ["busca", "buscar", "encuentra", "información"]):
        intent = "search"
    elif any(word in query_lower for word in ["analiza", "analizar", "análisis"]):
        intent = "analysis"  
    elif any(word in query_lower for word in ["verifica", "verificar", "es cierto", "fact check"]):
        intent = "fact_check"
    else:
        intent = "unknown"
    
    return {
        "intent": intent,
        "entities": {
            "title": title,
            "person": None, 
            "claim": query if intent == "fact_check" else None
        }
    }