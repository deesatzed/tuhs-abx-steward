"""
Audit Logger for TUHS Antibiotic Steward
Logs all recommendation requests and responses for compliance and review
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import os


DEFAULT_LOG_DIR = "logs"
DEFAULT_PREFIX = "audit"


def ensure_log_directory(log_dir: str = DEFAULT_LOG_DIR) -> Path:
    """Ensure the log directory exists"""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def build_log_file_path(log_dir: str = DEFAULT_LOG_DIR, date: Optional[datetime] = None) -> Path:
    """Build the log file path with date-based naming"""
    if date is None:
        date = datetime.now()

    log_path = ensure_log_directory(log_dir)

    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)

    filename = f"{DEFAULT_PREFIX}-{year}-{month}-{day}.log"
    return log_path / filename


def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove or redact sensitive information from logs"""
    sanitized = data.copy()

    # Redact API keys if present
    sensitive_keys = ['api_key', 'openrouter_api_key', 'authorization', 'token']
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"

    return sanitized


def record_audit_entry(
    request_id: str,
    input_data: Dict[str, Any],
    recommendation: Optional[str] = None,
    category: Optional[str] = None,
    tuhs_confidence: Optional[float] = None,
    final_confidence: Optional[float] = None,
    sources: Optional[list] = None,
    duration_ms: Optional[float] = None,
    status: str = "success",
    error: Optional[str] = None,
    log_dir: str = DEFAULT_LOG_DIR,
    timestamp: Optional[datetime] = None,
) -> None:
    """
    Record an audit entry for a recommendation request

    Args:
        request_id: Unique request identifier
        input_data: Patient data and request parameters
        recommendation: Generated recommendation text
        category: Infection category determined
        tuhs_confidence: TUHS guideline confidence score
        final_confidence: Final confidence after evidence search
        sources: List of evidence sources used
        duration_ms: Request processing time in milliseconds
        status: Request status (success/error)
        error: Error message if status is error
        log_dir: Directory for log files
        timestamp: Timestamp for the entry (defaults to now)
    """
    if timestamp is None:
        timestamp = datetime.now()

    log_file = build_log_file_path(log_dir, timestamp)

    # Build audit entry
    entry = {
        "timestamp": timestamp.isoformat(),
        "request_id": request_id,
        "status": status,
        "input": sanitize_for_logging(input_data),
        "category": category,
        "recommendation_length": len(recommendation) if recommendation else 0,
        "tuhs_confidence": tuhs_confidence,
        "final_confidence": final_confidence,
        "source_count": len(sources) if sources else 0,
        "duration_ms": duration_ms,
        "error": error,
    }

    # Write to log file (append mode)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_log_summary(log_dir: str = DEFAULT_LOG_DIR, date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Get summary statistics from audit logs

    Args:
        log_dir: Directory containing log files
        date: Date to analyze (defaults to today)

    Returns:
        Dictionary with summary statistics
    """
    if date is None:
        date = datetime.now()

    log_file = build_log_file_path(log_dir, date)

    if not log_file.exists():
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_requests": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_duration_ms": 0,
            "categories": {},
        }

    total_requests = 0
    success_count = 0
    error_count = 0
    total_duration = 0
    categories = {}

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                total_requests += 1

                if entry.get("status") == "success":
                    success_count += 1
                else:
                    error_count += 1

                if entry.get("duration_ms"):
                    total_duration += entry["duration_ms"]

                category = entry.get("category", "unknown")
                categories[category] = categories.get(category, 0) + 1

            except json.JSONDecodeError:
                continue

    return {
        "date": date.strftime("%Y-%m-%d"),
        "total_requests": total_requests,
        "success_count": success_count,
        "error_count": error_count,
        "avg_duration_ms": total_duration / total_requests if total_requests > 0 else 0,
        "categories": categories,
    }


if __name__ == "__main__":
    # Test the audit logger
    print("Testing audit logger...")

    test_request_id = f"test_{datetime.now().timestamp()}"
    test_input = {
        "age": "65",
        "gender": "male",
        "infection_type": "cystitis",
        "gfr": "80",
    }

    record_audit_entry(
        request_id=test_request_id,
        input_data=test_input,
        recommendation="Test recommendation",
        category="cystitis",
        tuhs_confidence=0.85,
        final_confidence=0.90,
        sources=["TUHS Guidelines", "IDSA"],
        duration_ms=1250.5,
        status="success",
    )

    print("✅ Test entry written to audit log")

    # Get summary
    summary = get_log_summary()
    print(f"\n📊 Log Summary for {summary['date']}:")
    print(f"   Total requests: {summary['total_requests']}")
    print(f"   Success: {summary['success_count']}")
    print(f"   Errors: {summary['error_count']}")
    print(f"   Avg duration: {summary['avg_duration_ms']:.2f}ms")
    print(f"   Categories: {summary['categories']}")
