import os, redis, datetime
from rq_scheduler import Scheduler
from jobs import sync_transfers

r = redis.from_url(os.environ["REDIS_URL"])
sch = Scheduler(queue_name="sync_transfers", connection=r)

first = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=15)
sch.schedule(scheduled_time=first, func=sync_transfers, interval=15, repeat=None)

print("Scheduled: sync_transfers() every 15s")
