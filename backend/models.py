from tortoise.models import Model
from tortoise import fields


class CallRecords(Model):
    id = fields.BigIntField(pk=True)
    master_id = fields.IntField(default=1)
    slave_id = fields.IntField()
    internal_id = fields.BigIntField(unique=True)
    status = fields.IntField()
    direction = fields.IntField()
    source_number = fields.CharField(max_length=50)
    destination_number = fields.CharField(max_length=50)
    call_started_datetime = fields.DatetimeField()
    call_ended_datetime= fields.DatetimeField()
    ringing_time = fields.IntField()
    talking_time = fields.IntField()
    audio_file = fields.TextField()
    internal_number = fields.CharField(max_length=50)
    unique_id = fields.TextField()
    service_data = fields.TextField()

    class Meta:
        table = 'CallRecords'
