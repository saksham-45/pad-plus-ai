import logging
import os
from typing import Optional, Any

logger = logging.getLogger("padplus.sentry_healer")

_SENTRY_TOKEN: Optional[str] = None
_HEALER_MODE: str = "monitor"

SENTRY_API_BASE = "https://o4511597299302400.ingest.de.sentry.io/api/4511597309984848"

ERROR_TO_DETECTOR: dict[str, str] = {
    "ProviderFailedError": "error_path",
    "AllProvidersFailedError": "error_path",
    "ConnectionError": "error_path",
    "TimeoutError": "latency_anomaly",
    "DatabaseError": "resource_leak",
    "MemoryError": "high_memory",
    "ImportError": "slow_import",
}


def configure(token: Optional[str] = None, mode: str = "monitor"):
    global _SENTRY_TOKEN, _HEALER_MODE
    if token:
        _SENTRY_TOKEN = token
    _HEALER_MODE = mode
    logger.info("Sentry-Healer bridge: mode=%s, token=%s", mode, "yes" if token else "no")


def _get_detector_for_error(error_type: str) -> str:
    return ERROR_TO_DETECTOR.get(error_type, "error_path")


async def handle_sentry_webhook(payload: dict) -> dict:
    """Обрабатывает webhook от Sentry.

    Sentry присылает:
    {
      "action": "created",
      "data": {
        "event": {"exception": {"values": [{"type": "...", "value": "..."}]}},
        "issue": {"id": "...", "title": "..."},
        ...
      }
    }
    """
    try:
        data = payload.get("data", {})
        event = data.get("event", {})
        issue = data.get("issue", {})

        exceptions = event.get("exception", {}).get("values", [])
        error_type = exceptions[0].get("type", "unknown") if exceptions else "unknown"
        error_value = exceptions[0].get("value", "") if exceptions else ""
        issue_title = issue.get("title", "unknown")
        issue_id = issue.get("id", "unknown")
        culprit = event.get("culprit", "")
        level = event.get("level", "error")

        logger.info(
            "Sentry webhook: issue=%s type=%s level=%s culprit=%s",
            issue_id, error_type, level, culprit,
        )

        # Маппинг ошибки на детектор HEALER
        detector = _get_detector_for_error(error_type)
        target_file = culprit.split(" ")[0] if culprit else "backend/main.py"

        # Запускаем HEALER диагностику
        result = await _run_healer_diagnostics(target_file, detector, {
            "error_type": error_type,
            "error_value": error_value,
            "issue_title": issue_title,
            "level": level,
        })

        # Помечаем issue тегами в Sentry
        tags = {
            "healer_action": result.get("action", "none"),
            "healer_status": result.get("status", "ok"),
            "healer_detector": detector,
        }
        if result.get("patched"):
            tags["healer_patched_files"] = ",".join(result["patched"])
        if result.get("reports", 0) > 0:
            tags["healer_reports"] = str(result["reports"])

        await _tag_sentry_issue(issue_id, tags)

        return {
            "handled": True,
            "issue_id": issue_id,
            "error_type": error_type,
            "healer_action": result.get("action", "none"),
            "healer_status": result.get("status", "ok"),
            "tags": tags,
        }

    except Exception as e:
        logger.error("Ошибка обработки Sentry webhook: %s", e)
        return {"handled": False, "error": str(e)}


async def _run_healer_diagnostics(
    target_file: str,
    detector: str,
    context: dict,
) -> dict:
    """Запускает HEALER диагностику для целевого файла."""
    try:
        import sys
        healer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "HEALER")
        if healer_path not in sys.path:
            sys.path.insert(0, healer_path)

        from healer.orchestrator import HealerOrchestrator, HealerMode

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        orch = HealerOrchestrator(project_path=project_root, mode=_HEALER_MODE)

        cycle = orch.run_cycle(quiet=True)

        action = "none"
        if cycle.status == "ok" and cycle.applied_count > 0:
            action = "patched"
        elif cycle.status == "rolled_back":
            action = "rolled_back"
        elif cycle.report_count > 0:
            action = "reported"

        return {
            "action": action,
            "status": cycle.status,
            "reports": cycle.report_count,
            "patched": cycle.patched_files,
            "summary": cycle.summary,
        }

    except ImportError as e:
        logger.warning("HEALER не загружен: %s", e)
        return {"action": "none", "status": "unavailable", "error": str(e)}
    except Exception as e:
        logger.error("Ошибка HEALER: %s", e)
        return {"action": "none", "status": "error", "error": str(e)}


async def get_sentry_issues() -> list[dict]:
    """Получает список нерешенных issues из Sentry API."""
    if not _SENTRY_TOKEN:
        logger.debug("Нет Sentry токена")
        return []

    try:
        import httpx

        org_slug = "pad-op"
        project_slug = "pad-ai"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/",
                headers={"Authorization": f"Bearer {_SENTRY_TOKEN}"},
                params={"query": "is:unresolved", "limit": 10},
            )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("Sentry API error: %s", resp.status_code)
            return []
    except Exception as e:
        logger.warning("Sentry API request error: %s", e)
        return []


async def _tag_sentry_issue(issue_id: str, tags: dict[str, str]) -> None:
    """Добавляет теги на Sentry issue через API.

    Теги сохраняются в Sentry и видны в UI -> раздел Tags.
    Используется для пометки: healer_action, healer_status, healer_detector.
    """
    if not _SENTRY_TOKEN or not issue_id:
        return

    try:
        import httpx

        org_slug = "pad-op"
        project_slug = "pad-ai"

        async with httpx.AsyncClient(timeout=10) as client:
            for key, value in tags.items():
                resp = await client.put(
                    f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/{issue_id}/tags/{key}/",
                    headers={"Authorization": f"Bearer {_SENTRY_TOKEN}"},
                    json={"value": value},
                )
                if resp.status_code not in (200, 201):
                    logger.debug("Sentry tag %s=%s -> %s", key, value, resp.status_code)

        logger.info("Sentry issue %s помечена тегами: %s", issue_id, tags)
    except Exception as e:
        logger.warning("Не удалось пометить Sentry issue %s: %s", issue_id, e)
