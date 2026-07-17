from huey import crontab
from huey.contrib.djhuey import db_periodic_task
from l4py import get_logger

from apps.authentication.services.user_profile import UserProfileService

logger = get_logger()


@db_periodic_task(crontab(minute="*/5"))
def heartbeat_deactivate_stale_users() -> None:
    """Example periodic job: demonstrates a Huey task calling into a Service
    instead of duplicating business logic or querying models directly."""
    service = UserProfileService()
    active_count = service.filter(is_active=True).count()
    logger.info("Heartbeat: %s active user profiles", active_count)
