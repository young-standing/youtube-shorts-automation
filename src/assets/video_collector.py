#!/usr/bin/env python3
"""Placeholder video collector - returns empty list for now."""

import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Return empty list for now
    result = []
    
    result_file = output_path / "videos.json"
    with open(result_file, "w") as f:
        json.dump(result, f)
    
    print(f"No videos collected (placeholder)")

if __name__ == "__main__":
    main()
