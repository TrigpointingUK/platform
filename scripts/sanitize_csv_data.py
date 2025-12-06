#!/usr/bin/env python3
"""
Sanitize CSV data to handle PostgreSQL compatibility issues.

This script cleans exported CSV files to:
- Remove NUL bytes (binary zeros)
- Convert invalid dates (0000-00-00) to NULL
- Convert pandas timedelta format to proper TIME format
- Handle other PostgreSQL incompatibilities

Usage:
    python scripts/sanitize_csv_data.py --input-dir /path/to/export
"""

import argparse
import csv
import re
from pathlib import Path
from typing import Optional


class CSVSanitizer:
    """Sanitize CSV files for PostgreSQL import."""

    def __init__(self, input_dir: str):
        """Initialize sanitizer with input directory."""
        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")

        print(f"Input directory: {self.input_dir}")
        self.files_processed = 0
        self.files_with_issues = 0

    @staticmethod
    def _has_time_overflow(value: str) -> bool:
        """
        Check if a time value has hours > 23 (overflow).

        Args:
            value: The time value to check

        Returns:
            True if time has overflow, False otherwise
        """
        if not value or " " in value:
            return False

        try:
            parts = value.split(":")
            if len(parts) == 3:
                hours = int(parts[0])
                return hours > 23
        except (ValueError, IndexError):
            pass

        return False

    @staticmethod
    def sanitize_value(value: str, column_name: str = "") -> str:
        """
        Sanitize a single CSV value.

        Args:
            value: The value to sanitize
            column_name: Optional column name for context-aware sanitization

        Returns:
            Sanitized value
        """
        if not value or value == "":
            return ""

        # Remove NUL bytes (binary null characters)
        if "\x00" in value:
            value = value.replace("\x00", "")

        # Convert invalid MySQL dates to empty (will become NULL)
        if value in ("0000-00-00", "0000-00-00 00:00:00"):
            return ""

        # Convert pandas timedelta format to TIME format
        # "0 days HH:MM:SS" -> "HH:MM:SS"
        if " days " in value and ":" in value:
            match = re.match(r"^(\d+) days (.+)$", value)
            if match:
                days = int(match.group(1))
                time_part = match.group(2)
                if days == 0:
                    # Just return the time part (but still check for overflow)
                    value = time_part
                else:
                    # For non-zero days: This represents a DURATION, not a TIME
                    # PostgreSQL TIME type doesn't support > 24 hours
                    # Cap at 23:59:59 as it's likely misused duration data
                    value = "23:59:59"

        # Handle TIME values that are too large for PostgreSQL TIME type
        # PostgreSQL TIME only supports 00:00:00 to 23:59:59
        # Cap hours at 23 for ANY time-like value (likely data error or duration misused as time)
        if ":" in value and " " not in value:
            try:
                parts = value.split(":")
                if len(parts) == 3:
                    hours = int(parts[0])
                    if hours > 23:
                        # Cap at 23:59:59 (probably bad data or duration stored as time)
                        # This applies to ALL HH:MM:SS format values, not just columns named "time"
                        return "23:59:59"
            except (ValueError, IndexError):
                pass  # Not a valid time format, leave as-is

        # Remove other control characters (keep newlines and tabs if intentional)
        value = "".join(char for char in value if char >= " " or char in "\n\r\t")

        # Strip unnecessary .0 from values that look like integers written as floats
        # E.g., "3207.0" -> "3207"
        if (
            value
            and value.endswith(".0")
            and value.replace(".", "").replace("-", "").isdigit()
        ):
            value = value[:-2]

        return value

    def sanitize_csv_file(self, csv_file: Path, dry_run: bool = False):
        """
        Sanitize a single CSV file (memory-efficient streaming).

        Args:
            csv_file: Path to CSV file
            dry_run: If True, only report issues without modifying files
        """
        print(f"\nProcessing: {csv_file.name}")

        # Quick scan of first 10MB to check for common issues (don't read entire file)
        has_nul_bytes = False
        has_invalid_dates = False
        has_timedelta = False
        has_empty_quoted = False

        try:
            with open(csv_file, "rb") as f:
                # Read first 10MB only for quick check
                sample = f.read(10 * 1024 * 1024).decode("utf-8", errors="replace")
                has_nul_bytes = "\x00" in sample
                has_invalid_dates = "0000-00-00" in sample
                has_timedelta = " days " in sample and ":" in sample
                # Check for TIME values with hours > 23 (e.g., "336:00:00")
                # Use regex to find patterns like "XXX:XX:XX" where XXX > 23
                import re

                time_overflow = bool(
                    re.search(r"\b([2-9]\d\d+|[3-9]\d):\d{2}:\d{2}\b", sample)
                )
                has_timedelta = has_timedelta or time_overflow
                # Check for quoted empty strings that should be NULL for COPY
                has_empty_quoted = '""' in sample
        except Exception as e:
            print(f"  ⚠️  Could not read file for sampling: {e}")

        # Always process to be safe, even if sample didn't show issues
        issues_found = []
        if has_nul_bytes:
            issues_found.append("NUL bytes")
        if has_invalid_dates:
            issues_found.append("invalid dates")
        if has_timedelta:
            issues_found.append("timedelta format")
        if has_empty_quoted:
            issues_found.append("empty quoted strings")

        if issues_found:
            self.files_with_issues += 1
            print(f"  ⚠️  Issues found: {', '.join(issues_found)}")

        if dry_run:
            print(f"  ℹ️  Dry run - no changes made")
            return

        # Always sanitize to handle issues that might be later in the file
        try:
            rows_processed = 0
            rows_sanitized = 0

            # Create temporary output file
            output_file = csv_file.with_suffix(".csv.tmp")

            # Process in streaming fashion with NUL byte filtering
            # Create a wrapper that strips NUL bytes on the fly
            class NulByteFilter:
                """Iterator that strips NUL bytes from file lines."""

                def __init__(self, file_obj):
                    self.file_obj = file_obj

                def __iter__(self):
                    return self

                def __next__(self):
                    line = next(self.file_obj)
                    return line.replace("\x00", "")

            with open(
                csv_file, "r", encoding="utf-8", errors="replace"
            ) as infile, open(
                output_file, "w", encoding="utf-8", newline=""
            ) as outfile:

                # Wrap the file object with NUL byte filter
                filtered_input = NulByteFilter(infile)
                reader = csv.DictReader(filtered_input)
                if not reader.fieldnames:
                    print(f"  ✗ No columns found")
                    return

                # For COPY compatibility, use QUOTE_MINIMAL and write NULLs as empty unquoted fields
                writer = csv.DictWriter(
                    outfile, fieldnames=reader.fieldnames, quoting=csv.QUOTE_MINIMAL
                )
                writer.writeheader()

                for row in reader:
                    rows_processed += 1
                    row_had_issues = False

                    # Check for rows with NULL primary key (first column)
                    # For tables like postcode8 where code is the PK and must not be NULL
                    first_col = list(row.keys())[0] if row else None
                    if first_col and not row.get(first_col):
                        # Skip rows where the first column (likely PK) is empty
                        rows_sanitized += 1
                        continue

                    # Sanitize each value
                    sanitized_row = {}
                    for key, value in row.items():
                        original_value = value

                        if value and (
                            "\x00" in value
                            or value in ("0000-00-00", "0000-00-00 00:00:00")
                            or (" days " in value and ":" in value)
                            or (
                                "time" in key.lower()
                                and ":" in value
                                and CSVSanitizer._has_time_overflow(value)
                            )
                        ):
                            row_had_issues = True

                        # Sanitize the value
                        value = CSVSanitizer.sanitize_value(value, key)

                        # For COPY compatibility: empty strings should be truly empty (NULL)
                        # not quoted empty strings ""
                        if value == "":
                            value = (
                                None  # This will be written as unquoted empty = NULL
                            )

                        sanitized_row[key] = value

                        if original_value != value:
                            row_had_issues = True

                    if row_had_issues:
                        rows_sanitized += 1

                    writer.writerow(sanitized_row)

                    # Progress indicator for large files
                    if rows_processed % 100000 == 0:
                        print(f"    Progress: {rows_processed:,} rows processed...")

            # Replace original file with sanitized version
            output_file.replace(csv_file)

            if rows_sanitized > 0:
                print(f"  ✓ Sanitized {rows_sanitized:,} of {rows_processed:,} rows")
            else:
                print(f"  ✓ Processed {rows_processed:,} rows (no changes needed)")

        except Exception as e:
            print(f"  ✗ Error sanitizing file: {e}")
            import traceback

            traceback.print_exc()

    def sanitize_all(self, dry_run: bool = False):
        """
        Sanitize all CSV files in the input directory.

        Args:
            dry_run: If True, only report issues without modifying files
        """
        print("\n" + "=" * 60)
        print("CSV Data Sanitization")
        print("=" * 60)

        if dry_run:
            print("\n🔍 DRY RUN MODE - No files will be modified\n")

        # Find all CSV files
        csv_files = sorted(self.input_dir.glob("*.csv"))
        print(f"\nFound {len(csv_files)} CSV files to process")

        for csv_file in csv_files:
            self.sanitize_csv_file(csv_file, dry_run=dry_run)
            self.files_processed += 1

        # Summary
        print("\n" + "=" * 60)
        print("Sanitization Summary")
        print("=" * 60)
        print(f"Files processed: {self.files_processed}")
        print(f"Files with issues: {self.files_with_issues}")

        if dry_run:
            print("\n🔍 This was a dry run. Re-run without --dry-run to apply changes.")
        else:
            print("\n✅ Sanitization complete!")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sanitize CSV files for PostgreSQL import"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="mysql_export",
        help="Directory containing CSV files (default: mysql_export)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report issues without modifying files",
    )

    args = parser.parse_args()

    sanitizer = CSVSanitizer(args.input_dir)
    sanitizer.sanitize_all(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
