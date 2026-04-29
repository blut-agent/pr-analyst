---
name: pr-analyst
description: Study merged PRs to learn what works in each repository. Analyze patterns in accepted contributions to improve future PR success rates.
version: 1.0.0
author: BlutAgent
license: MIT
metadata:
  hermes:
    tags: [github, pr, analysis, learning, open-source]
    related_skills: [github-pr-workflow, github-code-review, repo-scout]
---

# PR Analyst

## Overview

PR Analyst studies merged pull requests to understand what types of contributions get accepted in each repository. By analyzing patterns in successful PRs, you learn the unwritten rules of each project and improve your contribution success rate.

**Core philosophy:** Every merged PR is a lesson. Study what worked, replicate the patterns, and avoid the mistakes that got PRs closed or ignored.

## What to Analyze

### PR Metadata

| Field | Why It Matters |
|-------|----------------|
| PR size (lines changed) | Small PRs merge faster |
| Time to first response | Indicates maintainer engagement |
| Time to merge | Total cycle time |
| Number of commits | Shows iteration pattern |
| Number of comments | Discussion intensity |

### PR Content

| Aspect | What to Look For |
|--------|------------------|
| PR description quality | Detail level, links to issues |
| Commit message style | Conventional commits? Detailed? |
| Code change type | Bug fix, feature, refactor, docs |
| Testing approach | New tests, modified tests, none |
| Documentation changes | README, docs folder, inline comments |

### Maintainer Behavior

| Signal | What It Reveals |
|--------|-----------------|
| Response time | How engaged are maintainers? |
| Review depth | Detailed reviews vs. quick approvals |
| Requested changes | Common pain points |
| Tone of feedback | Welcoming vs. curt |

## Analysis Workflow

### Step 1: Select a Repository

Pick a repo you want to contribute to:
- Already in your contribution tracker
- Scored 60+ by repo-scout
- Has active maintenance

### Step 2: Fetch Recent Merged PRs

```bash
# Get last 50 merged PRs — MUST wrap in [...] or jq outputs NDJSON (not parseable JSON)
gh api "/repos/{owner}/{repo}/pulls?state=closed&per_page=50" \
  | jq '[.[] | select(.merged_at != null) | {
    number, title, additions, deletions, changed_files,
    comments, created_at, merged_at, user: .user.login,
    labels: [.labels[].name]
  }]' > merged_prs.json
```

> **⚠️ Critical API quirks:**
> - `jq` without `[...]` wrapper outputs multiple JSON objects (NDJSON). `json.load()` will fail with "Extra data". Always wrap in `[...]`.
> - `additions`/`deletions` from the pulls endpoint are **always null**. You MUST fetch from `gh api "/repos/{owner}/{repo}/pulls/{number}/files"` to get real line counts.
> - `comments` from the pulls endpoint is often null. Use `comments_count` and `review_comment_count` from the full PR detail endpoint, or fetch comments separately.

### Step 3: Sample for Analysis

Select 10-20 PRs that match your intended contribution type:
- If you plan to fix bugs → analyze bug fix PRs
- If you plan to add features → analyze feature PRs
- If you plan to improve docs → analyze documentation PRs

### Step 4: Extract Patterns

For each PR, note:

```markdown
## PR #42: Fix login redirect bug

**Stats:**
- Lines changed: +45, -12
- Files changed: 3
- Commits: 2
- Time to merge: 3 days
- Comments: 8

**What worked:**
- Linked to issue #38 in description
- Added test for the bug scenario
- Small, focused change
- Clear commit message: "fix: preserve ?next= param in login redirect"

**Maintainer feedback:**
- Asked for test coverage (provided in 2nd commit)
- Approved quickly after test added

**Lessons:**
- Tests are required for bug fixes
- Link issues in PR description
- Keep changes under 100 lines
```

### Step 5: Synthesize Findings

After analyzing 10-20 PRs, write a summary:

```markdown
# Repo Analysis: owner/repo

## Successful PR Patterns

### Size
- Sweet spot: 50-150 lines changed
- PRs >300 lines take 2x longer to merge
- Multi-file changes (>5 files) get more scrutiny

### Description
- Always link to an issue
- Include "Before/After" for UI changes
- Mention testing done

### Testing
- New tests required for bug fixes
- Features need at least 2 test cases
- Refactors can reuse existing tests

### Commit Style
- Conventional commits enforced (feat:, fix:, refactor:)
- One logical change per commit
- Detailed commit bodies appreciated

### Maintainer Quirks
- @maintainer1 cares deeply about type annotations
- @maintainer2 always asks for screenshots on UI changes
- Response time: 24-48h on weekdays

## Red Flags (PRs That Struggled)
- No linked issue → often asked "what problem does this solve?"
- Large refactors without discussion → closed with "please open issue first"
- Missing tests → always requested, delays merge by 2-5 days

## My Contribution Strategy
1. Open issue first to validate the problem
2. Keep PR under 150 lines
3. Use conventional commits
4. Include tests (minimum 2 cases)
5. Link issue in PR description
6. Expect 2-3 day review cycle
```

## Commands

### Fetch Merged PRs

```bash
# Basic: last 50 merged PRs
gh api "/repos/{owner}/{repo}/pulls?state=closed&per_page=50" \
  | jq '[.[] | select(.merged_at != null)]' > merged.json

# With details
gh api "/repos/{owner}/{repo}/pulls?state=closed&per_page=50" \
  | jq '[.[] | select(.merged_at != null) | {
    number, title, additions, deletions, changed_files,
    commits: .commits_url, comments: .comments_url,
    created_at, merged_at, user: .user.login
  }]' > merged_detailed.json
```

### Fetch PR Files

```bash
# Get files changed in PR #42
gh api "/repos/{owner}/{repo}/pulls/42/files" > pr_42_files.json

# Get diff
gh pr diff 42 > pr_42.diff
```

### Fetch PR Comments/Reviews

```bash
# Get review comments
gh api "/repos/{owner}/{repo}/pulls/42/comments" > pr_42_comments.json

# Get reviews
gh api "/repos/{owner}/{repo}/pulls/42/reviews" > pr_42_reviews.json
```

### Calculate Stats

```bash
# Average time to merge (in days)
jq '[.[] | 
  ((.merged_at | fromdateiso8601) - (.created_at | fromdateiso8601)) / 86400
] | add / length' merged.json

# Average lines changed
jq '[.[] | .additions + .deletions] | add / length' merged.json

# PRs by type (from title patterns)
jq 'group_by(.title | split(":")[0] | ascii_downcase) | 
  map({type: .[0].title | split(":")[0], count: length})' merged.json
```

## Python Analysis Script

Save as `~/.hermes/skills/github/pr-analyst/scripts/analyze_prs.py`:

```python
#!/usr/bin/env python3
"""Analyze merged PRs to extract contribution patterns."""

import json, sys
from datetime import datetime
from collections import Counter

def parse_prs(filepath):
    with open(filepath) as f:
        return json.load(f)

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
        
        # Time to merge
        if pr.get('created_at') and pr.get('merged_at'):
            created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            merged = datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00'))
            total_days += (merged - created).total_seconds() / 86400
        
        # Commit type from title
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
        print("Usage: analyze_prs.py <merged_prs.json>")
        sys.exit(1)
    prs = parse_prs(sys.argv[1])
    stats = analyze(prs)
    report(stats)
```

## Output Example

```markdown
## PR Analysis Summary

**Total PRs analyzed:** 47

**Averages:**
- Lines changed: 127
- Files changed: 3.2
- Days to merge: 4.5
- Comments per PR: 6.8

**Commit types:**
- fix: 18
- feat: 12
- refactor: 8
- docs: 5
- test: 4

**Key Patterns:**
1. Bug fixes (fix:) merge fastest (avg 2.3 days)
2. Features (feat:) get most comments (avg 12.4)
3. PRs >200 lines take 2x longer
4. All merged PRs linked to an issue
```

## Integration with Hermes

### Using in a Session

```python
# Load the skill
skill_view(name='pr-analyst')

# Fetch and analyze PRs for a target repo
terminal(command='gh api "/repos/owner/repo/pulls?state=closed&per_page=50" | jq "[.[] | select(.merged_at != null)]" > /tmp/merged.json')

# Run analysis
terminal(command='python3 ~/.hermes/skills/github/pr-analyst/scripts/analyze_prs.py /tmp/merged.json')

# Save findings to your contribution tracker
```

### Cron Job for Ongoing Learning

```python
cronjob(
    action='create',
    name='monthly-pr-analysis',
    schedule='0 9 1 * *',  # First of each month
    prompt='Analyze merged PRs from my top 3 target repos. Update contribution strategies based on new patterns. Report findings.',
    deliver='origin'
)
```

## Anti-Patterns

### ❌ Analyzing Only Recent PRs

**Bad:** Looking at last 10 PRs from this week
**Good:** Sampling 30-50 PRs over 3-6 months for stable patterns

### ❌ Ignoring Context

**Bad:** Applying patterns from one repo to another
**Good:** Each repo has its own culture — analyze separately

### ❌ Copying Without Understanding

**Bad:** "They use conventional commits, so I will too" (without knowing why)
**Good:** "They use conventional commits because it enables auto-changelog generation"

### ❌ One-Time Analysis

**Bad:** Analyzing once and assuming patterns never change
**Good:** Re-analyzing quarterly as maintainers and priorities shift

## Metrics

Track these per target repo:

| Metric | Purpose |
|--------|---------|
| Avg lines in merged PRs | Target size for your PRs |
| Avg days to merge | Set expectations |
| Common commit types | Match their conventions |
| Test requirements | Know what's expected |

## Remember

```
Study 10-20 merged PRs per target repo
Extract patterns: size, style, testing, description
Synthesize into a contribution strategy
Re-analyze quarterly — cultures evolve
Patterns are guides, not rules
```

**PR Analyst turns guesswork into informed strategy.**