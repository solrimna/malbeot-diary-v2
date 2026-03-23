from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.alarm_service import get_due_alarms, trigger_alarm

scheduler = AsyncIOScheduler()


def send_alarm(alarm):
    print(
        f"[ALARM] user_id={alarm.user_id}, "
        f"alarm_id={alarm.id}, "
        f"time={alarm.alarm_time}, "
        f"repeat_days={alarm.repeat_days}"
    )


async def check_alarms():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id))
        user_ids = result.scalars().all()

        due_alarms = []
        for user_id in user_ids:
            user_due_alarms = await get_due_alarms(db, user_id)
            due_alarms.extend(user_due_alarms)

        for alarm in due_alarms:
            send_alarm(alarm)
            await trigger_alarm(db, alarm)


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_alarms, "interval", seconds=30, id="check_alarms")
        scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()