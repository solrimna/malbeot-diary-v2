from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alarm import Alarm


async def get_due_alarms(db: AsyncSession, user_id):
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    weekday_map = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    today = weekday_map[now.weekday()]

    result = await db.execute(
        select(Alarm).where(
           Alarm.user_id == user_id,
            Alarm.is_enabled.is_(True),
        )
    )
    alarms = result.scalars().all()

    due_alarms = []

    for alarm in alarms:
        # 알람 시간이 없으면 건너뛰기
        if not alarm.alarm_time:
            continue

        # 반복 요일이 없으면 건너뛰기
        if not alarm.repeat_days:
            continue

        alarm_time_str = alarm.alarm_time.strftime("%H:%M")
        repeat_days_list = [
            day.strip() for day in alarm.repeat_days.split(",") if day.strip()
        ]

        # 현재 시간과 알람 시간이 다르면 건너뛰기
        if alarm_time_str != current_time:
            continue

        # 오늘 요일이 반복 요일에 없으면 건너뛰기
        if today not in repeat_days_list:
            continue

        # 같은 분에 이미 실행됐으면 중복 실행 방지
        if alarm.last_triggered_at:
            last_triggered = alarm.last_triggered_at.replace(second=0, microsecond=0)
            current_minute = now.replace(second=0, microsecond=0)

            if last_triggered == current_minute:
                continue

        due_alarms.append(alarm)

    return due_alarms


async def trigger_alarm(db: AsyncSession, alarm: Alarm):
    """
    알람 1개를 실제로 실행하는 함수
    여기서 알림 전송, 메시지 생성, 일기 생성 같은 동작을 넣으면 됨
    """
    print(f"[ALARM TRIGGERED] id={alarm.id}, time={alarm.alarm_time}")

    # 마지막 실행 시각 갱신
    alarm.last_triggered_at = datetime.now()

    db.add(alarm)
    await db.commit()
    await db.refresh(alarm)


async def process_due_alarms(db: AsyncSession):
    """
    지금 울려야 하는 알람들을 찾아서 하나씩 실행
    """
    due_alarms = await get_due_alarms(db)

    for alarm in due_alarms:
        await trigger_alarm(db, alarm)