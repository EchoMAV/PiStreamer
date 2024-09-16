from typing import Optional
import uuid
from peewee import SqliteDatabase, Model, CharField, DateTimeField, UUIDField
from datetime import datetime
from constants import CommandStatus, PiCameraCommand

db = SqliteDatabase('library.db')

class CommandModel(Model):
    """ 
    This is where commands that were originally triggered via the GCS get stored
    for the PiStreamer to receive and execute. Generally the MavLinkCamera service only writes new
    rows to the table. The PiStreamer will read rows and update their status.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    command_type = CharField(index=True,choices=[(status.value, status.name) for status in PiCameraCommand])
    command_value = CharField(null=True)
    command_status = CharField(index=True,choices=[(status.value, status.name) for status in CommandStatus])

    class Meta:
        database = db

def initialize_db():
    """ 
    This method is called by the RPi automatically as part of boot up.
    """
    db.connect()
    db.create_tables([CommandModel])
    db.close()

def add_command(command_value:PiCameraCommand, command_status:CommandStatus) -> None:
    with db.atomic():
        CommandModel.create(
            created_at=datetime.now(),
            command_value=command_value,
            command_status=command_status
        )

def get_pending_commands() -> Optional[CommandModel]:
    """ 
    Returns the oldest command that has not been executed yet (i.e. pending).
    If no such commands exist, then None is returned.
    """
    with db.atomic():
        return CommandModel.select().where(CommandModel.command_status == CommandStatus.PENDING.value).order_by(CommandModel.created_at.asc()).first()

def update_command_status(command_id:str, new_status:CommandStatus) -> None:
    with db.atomic():
        query = CommandModel.update(command_status=new_status).where(CommandModel.id == command_id)
        query.execute()