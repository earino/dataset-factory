"""Conservative worker admission charges; estimates, never provider invoices."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import math


def completed_hours(record):
    """Only confirmed, identified deletions can release unused reservations."""
    if record.get('status') != 'deleted' or not record.get('server_id'):
        return None
    try:
        start = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(record['deleted_at'].replace('Z', '+00:00'))
        if start.utcoffset() is None or end.utcoffset() is None or end < start:
            return None
        return max(1, math.ceil((end - start).total_seconds() / 3600))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None


def completed_charge(record, rate_key='rate_ceiling_eur'):
    hours = completed_hours(record)
    try:
        rate = Decimal(str(record[rate_key]))
        if hours is None or not rate.is_finite() or rate <= 0:
            return None
        return rate * hours
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return None


def monthly_usage(records, period):
    """Charge full lifetime to both affected months, preserving boundary conservatism."""
    settled = reserved = Decimal('0')
    settled_jobs = reserved_jobs = 0
    for record in records:
        if period not in record['budget_months']:
            continue
        charge = completed_charge(record)
        if charge is None:
            reserved += Decimal(record['reservation_eur'])
            reserved_jobs += 1
        else:
            settled += charge
            settled_jobs += 1
    return {'completed_estimate_eur': str(settled), 'retained_reservations_eur': str(reserved),
            'charged_eur': str(settled + reserved), 'completed_jobs': settled_jobs,
            'reserved_jobs': reserved_jobs}
