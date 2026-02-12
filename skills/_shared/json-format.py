#!/usr/bin/env python3
"""JSON formatting utility for agent skill output.

Reads JSON from stdin and outputs it formatted for readability.
Supports filtering, field selection, and tabular output.

Usage:
    echo '{"key": "value"}' | python3 json-format.py
    echo '[...]' | python3 json-format.py --fields name,status
    echo '[...]' | python3 json-format.py --table name,status
"""

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Format JSON output")
    parser.add_argument(
        "--fields",
        help="Comma-separated list of fields to extract from each object",
    )
    parser.add_argument(
        "--table",
        help="Comma-separated list of fields to display as a table",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no indentation)",
    )
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    if args.table:
        fields = [f.strip() for f in args.table.split(",")]
        if isinstance(data, list):
            # Print header
            print("\t".join(fields))
            print("\t".join("-" * len(f) for f in fields))
            # Print rows
            for item in data:
                if isinstance(item, dict):
                    row = [str(item.get(f, "")) for f in fields]
                    print("\t".join(row))
        else:
            print("ERROR: --table requires a JSON array", file=sys.stderr)
            sys.exit(1)
    elif args.fields:
        fields = [f.strip() for f in args.fields.split(",")]
        if isinstance(data, list):
            result = [{f: item.get(f) for f in fields} for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            result = {f: data.get(f) for f in fields}
        else:
            result = data
        indent = None if args.compact else 2
        print(json.dumps(result, indent=indent, default=str))
    else:
        indent = None if args.compact else 2
        print(json.dumps(data, indent=indent, default=str))


if __name__ == "__main__":
    main()
