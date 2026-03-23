from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
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
        due_alarms = await get_due_alarms(db)

        for alarm in due_alarms:
            send_alarm(alarm)
            await trigger_alarm(db, alarm)


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            check_alarms,
            "interval",
            minutes=1,
            id="check_alarms_job",
            replace_existing=True,
        )
        scheduler.start()
        print("[SCHEDULER] started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[SCHEDULER] stopped")