from celery.decorators import periodic_task
from celery import shared_task
from ScoutSuite.scan import run
from celery.task.schedules import crontab
from django.utils import timezone
from .models import Account

@shared_task
def runscan(aws_access_key_id,aws_secret_access_key):
    run("aws",aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)


@periodic_task(run_every=(crontab(minute='0', hour='0')), name="run_daily")
# @periodic_task(run_every=(crontab(minute='*')), name="run_daily")
def run_scan_daily():
    for account in Account.objects.all():
        account.last_scan_time = timezone.now()
        account.save()
        run("aws",aws_access_key_id=account.aws_access_key,aws_secret_access_key=account.aws_secret_key)