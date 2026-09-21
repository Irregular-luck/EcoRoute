from celery import shared_task
from .services import build_recommendations, persist_recommendations


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def refresh_route_analysis(source: str, destination: str) -> int:
    result = build_recommendations(source, destination)
    return len(persist_recommendations(result))
