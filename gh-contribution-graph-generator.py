import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from tqdm import tqdm


def generate_contribution_histogram(
    username: str, repo_owner: str, repo_name: str, output_dir: str = ".", exclude_authored_from_reviewed: bool = False
):
    """
    Generate a contribution histogram for a user's PRs in a specific repository.

    Args:
        username (str): GitHub username to analyze
        repo_owner (str): Owner of the repository
        repo_name (str): Name of the repository
        output_dir (str): Directory to save the output PNG file
        exclude_authored_from_reviewed (bool): Whether to exclude PRs authored by the user from the reviewed count
    """
    # GitHub API setup
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable is not set")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    HEADERS = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    def run_graphql_query(query, variables=None):
        response = requests.post(
            "https://api.github.com/graphql",
            headers=HEADERS,
            json={"query": query, "variables": variables},
        )
        if response.status_code != 200:
            raise Exception(f"Query failed: {response.status_code} - {response.text}")
        return response.json()

    def get_month_year(date_str):
        # Handle both formats: with and without timezone
        if "+" in date_str:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
        else:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        return date.strftime("%Y-%m")

    def fetch_prs_with_cursor(query, variables, desc):
        prs = []
        has_next_page = True
        end_cursor = None

        with tqdm(desc=desc) as pbar:
            while has_next_page:
                variables["cursor"] = end_cursor
                result = run_graphql_query(query, variables)

                if "errors" in result:
                    raise Exception(f"GraphQL Error: {result['errors']}")

                prs_data = result["data"]["search"]["edges"]
                prs.extend([edge["node"] for edge in prs_data])

                page_info = result["data"]["search"]["pageInfo"]
                has_next_page = page_info["hasNextPage"]
                end_cursor = page_info["endCursor"]

                pbar.update(len(prs_data))

        return prs

    # GraphQL query template
    prs_query = """
    query($cursor: String, $searchQuery: String!) {
      search(
        query: $searchQuery
        type: ISSUE
        first: 100
        after: $cursor
      ) {
        edges {
          node {
            ... on PullRequest {
              createdAt
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    # Fetch authored PRs
    print(f"Fetching PRs authored by {username}...")
    authored_variables = {
        "searchQuery": f"repo:{repo_owner}/{repo_name} is:pr author:{username}"
    }
    authored_prs = fetch_prs_with_cursor(
        prs_query, authored_variables, "Fetching authored PRs"
    )
    authored_dates = [get_month_year(pr["createdAt"]) for pr in authored_prs]

    # Fetch reviewed PRs
    print(f"\nFetching PRs reviewed by {username}...")
    reviewed_query = f"repo:{repo_owner}/{repo_name} is:pr reviewed-by:{username}"
    if exclude_authored_from_reviewed:
        reviewed_query += f" -author:{username}"
    reviewed_variables = {
        "searchQuery": reviewed_query
    }
    reviewed_prs = fetch_prs_with_cursor(
        prs_query, reviewed_variables, "Fetching reviewed PRs"
    )
    reviewed_dates = [get_month_year(pr["createdAt"]) for pr in reviewed_prs]

    # Create DataFrames for counting
    authored_df = (
        pd.DataFrame(authored_dates, columns=["month"])
        .groupby("month")
        .size()
        .reset_index(name="authored_count")
    )
    reviewed_df = (
        pd.DataFrame(reviewed_dates, columns=["month"])
        .groupby("month")
        .size()
        .reset_index(name="reviewed_count")
    )

    # Merge DataFrames
    merged_df = pd.merge(authored_df, reviewed_df, on="month", how="outer").fillna(0)
    merged_df["month"] = pd.to_datetime(merged_df["month"], format="%Y-%m")
    merged_df = merged_df.sort_values("month")

    # Plot histogram
    plt.figure(figsize=(12, 6))
    bar_width = 0.35
    x = range(len(merged_df["month"]))

    # Calculate totals
    total_authored = int(sum(merged_df["authored_count"]))
    total_reviewed = int(sum(merged_df["reviewed_count"]))

    # Plot bars
    plt.bar(
        [i - bar_width / 2 for i in x],
        merged_df["authored_count"],
        bar_width,
        label=f"PRs Authored (Total: {total_authored:,})",
        color="skyblue",
    )
    plt.bar(
        [i + bar_width / 2 for i in x],
        merged_df["reviewed_count"],
        bar_width,
        label=f"PRs Reviewed (Total: {total_reviewed:,})",
        color="lightcoral",
    )

    # Add total annotations
    plt.annotate(
        f"Total Authored: {total_authored:,}",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", fc="skyblue", alpha=0.3),
    )
    plt.annotate(
        f"Total Reviewed: {total_reviewed:,}",
        xy=(0.02, 0.90),
        xycoords="axes fraction",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3", fc="lightcoral", alpha=0.3),
    )

    plt.xlabel("Month")
    plt.ylabel("Number of Pull Requests")
    plt.title(f"Contribution History of {username} in {repo_owner}/{repo_name}")
    plt.xticks(x, merged_df["month"].dt.strftime("%Y-%m"), rotation=45)
    plt.legend()
    plt.tight_layout()

    # Save the plot
    output_filename = (
        output_path / f"{username}-{repo_owner}-{repo_name}-contribution-histogram.png"
    )
    plt.savefig(output_filename)
    print(f"\nContribution histogram saved as: {output_filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gh-contribution-graph-generator.py --target <username,owner/repo> [--exclude-authored-from-reviewed]")
        print(
            "Example: python gh-contribution-graph-generator.py --target peterxcli,apache/ozone --exclude-authored-from-reviewed"
        )
        sys.exit(1)


    # Parse command line arguments
    exclude_authored_from_reviewed = False
    targets = None
    output_dir = "."

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--exclude-authored-from-reviewed":
            exclude_authored_from_reviewed = True
            i += 1
        elif sys.argv[i] == "--targets":
            if i + 1 >= len(sys.argv):
                print("Error: --target requires a value")
                sys.exit(1)
            target = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output-dir":
            if i + 1 >= len(sys.argv):
                print("Error: --output-dir requires a value")
                sys.exit(1)
            output_dir = sys.argv[i + 1]
            i += 2
        else:
            print(f"Error: Unknown option {sys.argv[i]}")
            sys.exit(1)

    if not target:
        print("Error: --target is required")
        sys.exit(1)

    parsed_targets = []
    # Parse targets
    try:
        target_arr = target.split(" ")
        for target in target_arr:
            username, repo = target.split(",")
            repo_owner, repo_name = repo.split("/")
            parsed_targets.append((username, repo_owner, repo_name))
    except ValueError as e:
        print(f"Error parsing target '{target}': {str(e)}")
        print("Expected format: username,owner/repo")
        sys.exit(1)

    for target in parsed_targets:
        try:
            generate_contribution_histogram(
                target[0], target[1], target[2], output_dir, exclude_authored_from_reviewed
            )
        except Exception as e:
            print(
                f"Error generating histogram for {target[0]} in {target[1]}/{target[2]}: {str(e)}"
            )
            sys.exit(1)
