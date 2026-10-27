import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    action: str
    target_entity: str
    ip_address: str
    details: Dict[str, Any]
    timestamp: datetime