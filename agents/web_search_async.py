import anyio
from agents.web_search import web_search_agent

async def web_search_agent_async(title: str):
    """
    Ejecuta el web_search_agent SINCRÓNICO dentro de un hilo,
    para que pueda usarse en FastAPI.
    """
    return await anyio.to_thread.run_sync(web_search_agent, title)
