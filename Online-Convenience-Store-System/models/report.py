"""
Report model - created by Manager. Stores generated report data.
"""
from datetime import datetime
from typing import Optional


class Report:
    """A generated system report (inventory, orders, etc.)."""

    def __init__(self, report_id: str, report_type: str,
                 generated_at: datetime, data: dict,
                 requested_by=None, start_date=None, end_date=None):
        self.report_id = report_id
        self.report_type = report_type
        self.generated_at = generated_at
        self.data = data
        self.requested_by = requested_by  # Admin who requested it
        
        # Time boundaries (CRC 4.19)
        self.start_date = start_date or datetime(2000, 1, 1)
        self.end_date = end_date or datetime.now()

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "generated_at": self.generated_at.isoformat(),
            "data": self.data,
            "requested_by": self.requested_by.username if self.requested_by else None,
            "start_date": self.start_date.isoformat(),  
            "end_date": self.end_date.isoformat(),
        }