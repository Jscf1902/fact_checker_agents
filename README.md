# 🎯 Fact-Checker de Cine y Televisión con Web Scraping + LLM + Validación Semántica

Sistema inteligente para consulta, análisis y verificación de información sobre *películas y series*, basado en:

- *Web Scraping avanzado (TMDB)*
- *NLP con LLM (Qwen)*
- *Fact-Checking semántico*
- *Generación automática de reportes (.md)*
- *Interfaz web propia*

Este proyecto interpreta lenguaje natural, obtiene datos reales desde TMDB en tiempo real y valida afirmaciones relacionadas con el contenido audiovisual.

---

## 🏛 Arquitectura del Sistema

```mermaid
flowchart LR
    User --> UI --> API
    API --> NLP[NLP Agent]
    NLP -->|identifica intención y título| Coordinator
    Coordinator --> Scraper[Web Scraper TMDB]
    Coordinator --> FactChecker
    Coordinator --> Reporter
    Scraper --> Evidence
    FactChecker --> Evaluation
    Reporter --> Report.md
