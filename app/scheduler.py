from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.redis_service import update_redis_from_drive
from app.core import settings

scheduler = AsyncIOScheduler()


async def start_scheduler():
    scheduler.add_job(
        update_redis_from_drive,
        'interval',
        hours=settings.SCHEDULER_INTERVAL_HOURS,
        coalesce=True,
        misfire_grace_time=settings.SCHEDULER_INTERVAL_HOURS,
    )
    try:
        scheduler.start()
    except Exception as e:
        print(f"❌ Error starting scheduler: {str(e)}")
