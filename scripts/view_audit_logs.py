#!/usr/bin/env python3
"""
Utility script to view and analyze audit logs
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add parent directory to path so we can import audit_logger
sys.path.insert(0, str(Path(__file__).parent.parent))
from audit_logger import get_log_summary, DEFAULT_LOG_DIR


def view_today():
    """View today's audit log summary"""
    summary = get_log_summary()
    print_summary(summary)


def view_date(date_str):
    """View audit log summary for a specific date"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        summary = get_log_summary(date=target_date)
        print_summary(summary)
    except ValueError:
        print(f"❌ Invalid date format: {date_str}")
        print("   Use YYYY-MM-DD format (e.g., 2025-10-04)")


def view_recent(days=7):
    """View audit log summaries for the past N days"""
    print(f"\n📊 Audit Log Summary - Past {days} Days")
    print("=" * 80)

    for i in range(days):
        target_date = datetime.now() - timedelta(days=i)
        summary = get_log_summary(date=target_date)

        if summary['total_requests'] > 0:
            print(f"\n{summary['date']}: {summary['total_requests']} requests")
            print(f"  ✅ Success: {summary['success_count']} | ❌ Errors: {summary['error_count']}")
            print(f"  ⏱️  Avg duration: {summary['avg_duration_ms']:.2f}ms")
            if summary['categories']:
                print(f"  📂 Categories: {summary['categories']}")


def view_raw(date_str=None):
    """View raw audit log entries"""
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"❌ Invalid date format: {date_str}")
            return
    else:
        target_date = datetime.now()

    log_dir = Path(DEFAULT_LOG_DIR)
    year = target_date.year
    month = str(target_date.month).zfill(2)
    day = str(target_date.day).zfill(2)
    log_file = log_dir / f"audit-{year}-{month}-{day}.log"

    if not log_file.exists():
        print(f"❌ No audit log found for {target_date.strftime('%Y-%m-%d')}")
        return

    print(f"\n📄 Raw Audit Log: {log_file}")
    print("=" * 80)

    with open(log_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    entry = json.loads(line)
                    print(f"\n--- Entry {i} ---")
                    print(json.dumps(entry, indent=2))
                except json.JSONDecodeError:
                    print(f"⚠️  Line {i}: Invalid JSON")


def print_summary(summary):
    """Print formatted summary"""
    print("\n" + "=" * 80)
    print(f"📊 Audit Log Summary for {summary['date']}")
    print("=" * 80)
    print(f"\n📈 Total Requests: {summary['total_requests']}")
    print(f"   ✅ Successful: {summary['success_count']}")
    print(f"   ❌ Failed: {summary['error_count']}")
    print(f"   ⏱️  Average Duration: {summary['avg_duration_ms']:.2f}ms")

    if summary['categories']:
        print(f"\n📂 Infection Categories:")
        for category, count in sorted(summary['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"   • {category}: {count}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="View TUHS Antibiotic Steward audit logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View today's summary
  python view_audit_logs.py

  # View specific date
  python view_audit_logs.py --date 2025-10-04

  # View past 7 days
  python view_audit_logs.py --recent 7

  # View raw log entries
  python view_audit_logs.py --raw
  python view_audit_logs.py --raw --date 2025-10-04
        """
    )

    parser.add_argument(
        '--date',
        type=str,
        help='Specific date to view (YYYY-MM-DD format)'
    )

    parser.add_argument(
        '--recent',
        type=int,
        metavar='DAYS',
        help='View summary for past N days'
    )

    parser.add_argument(
        '--raw',
        action='store_true',
        help='View raw log entries instead of summary'
    )

    args = parser.parse_args()

    if args.raw:
        view_raw(args.date)
    elif args.recent:
        view_recent(args.recent)
    elif args.date:
        view_date(args.date)
    else:
        view_today()


if __name__ == "__main__":
    main()
