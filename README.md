# OSS Contribution Graph Generator

A GitHub Action that generates contribution graph showing the number of pull requests authored and reviewed by a user in specific repositories over time.

## Usage

```yaml
- uses: peterxcli/gh-contribution-graph-action@v1.3
  with:
    targets: 'username,owner/repo [username,owner/repo ...]'
    github_token: ${{ secrets.GITHUB_TOKEN }}
    output_dir: 'path/to/output'  # Optional, defaults to current directory
    exclude_authored_from_reviewed: true  # Optional, defaults to false
```

### Inputs

- `targets`: Comma-separated list of targets in the format `username,owner/repo`. Multiple targets can be specified with spaces.
- `github_token`: GitHub token for API access. Required for authentication.
- `output_dir`: Directory where the generated PNG files will be saved. Optional, defaults to the current directory.
- `exclude_authored_from_reviewed`: Whether to exclude PRs authored by the user from the reviewed count. Optional, defaults to `false`.

### Example

```yaml
name: Generate Contribution Histogram

on:
  workflow_dispatch:
    inputs:
      targets:
        description: 'Target repositories and usernames'
        required: true
        default: 'peterxcli,apache/ozone'

jobs:
  generate-histogram:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: peterxcli/gh-contribution-graph-action@v1.3
        with:
          targets: ${{ github.event.inputs.targets }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          output_dir: 'histograms'
```

## Output

The action generates PNG files named in the format:
`{username}-{repo_owner}-{repo_name}-contribution-graph.svg`

Each histogram shows:
- Number of PRs authored by the user (blue bars)
- Number of PRs reviewed by the user (red bars)
- Total counts for both authored and reviewed PRs
- Monthly breakdown of contributions

Example:

![peterxcli-apache-ozone-contribution-histogram](https://raw.githubusercontent.com/peterxcli/peterxcli/refs/heads/main/histograms/peterxcli-apache-ozone-contribution-graph.svg)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
