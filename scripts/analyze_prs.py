#!/usr/bin/env python3
"""Analyze merged PRs to extract contribution patterns.

Security hardened v1.1.0:
- Input file path validation
- JSON parse error handling
"""

import json, sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# Security: Restrict file access
ALLOWED_DIR = Path('/tmp').resolve()

def validate_file_path(filepath):
    """Validate file path is within allowed directory."""
    path = Path(filepath).resolve()
    if not str(path).startswith(str(ALLOWED_DIR)):
        raise ValueError(f"File must be in {ALLOWED_DIR}, got: {path}")
    if not path.suffix == '.json':
        raise ValueError(f"File must be .json, got: {path.suffix}")
    return path

def parse_prs(filepath):
    """Parse PRs from validated JSON file."""
    validated_path = validate_file_path(filepath)
    try:
        with open(validated_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

def analyze(prs):
    stats = {
        'total': len(prs),
        'avg_lines': 0,
        'avg_files': 0,
        'avg_merge_days': 0,
        'commit_types': Counter(),
        'avg_comments': 0,
    }
    
    total_lines, total_files, total_days, total_comments = 0, 0, 0, 0
    
    for pr in prs:
        total_lines += pr.get('additions', 0) + pr.get('deletions', 0)
        total_files += pr.get('changed_files', 0)
        total_comments += pr.get('comments', 0)
        
        if pr.get('created_at') and pr.get('merged_at'):
            try:
                created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                merged = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
                total_days += (merged - created).total_seconds() / 86400
            except (ValueError, TypeError):
                pass
        
        title = pr.get('title', '')
        if ':' in title:
            commit_type = title.split(':')[0].lower()
            stats['commit_types'][commit_type] += 1
    
    n = len(prs)
    if n > 0:
        stats['avg_lines'] = total_lines / n
        stats['avg_files'] = total_files / n
        stats['avg_merge_days'] = total_days / n
        stats['avg_comments'] = total_comments / n
    
    return stats

def report(stats):
    print(f"## PR Analysis Summary\n")
    print(f"**Total PRs analyzed:** {stats['total']}\n")
    print(f"**Averages:**")
    print(f"- Lines changed: {stats['avg_lines']:.0f}")
    print(f"- Files changed: {stats['avg_files']:.1f}")
    print(f"- Days to merge: {stats['avg_merge_days']:.1f}")
    print(f"- Comments per PR: {stats['avg_comments']:.1f}\n")
    print(f"**Commit types:**")
    for ctype, count in stats['commit_types'].most_common(5):
        print(f"- {ctype}: {count}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: analyze_prs.py <merged_prs.json>", file=sys.stderr)
        sys.exit(1)
    
    try:
        prs = parse_prs(sys.argv[1])
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    stats = analyze(prs)
    report(stats)
