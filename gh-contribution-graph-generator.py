import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from tqdm import tqdm
import click
import matplotlib.style as mplstyle


def generate_contribution_histogram(
    username: str,
    repo_owner: str,
    repo_name: str,
    output_dir: str = ".",
    exclude_authored_from_reviewed: bool = False,
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
    reviewed_variables = {"searchQuery": reviewed_query}
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
    total_authored = merged_df["authored_count"].sum()
    total_reviewed = merged_df["reviewed_count"].sum()

    # Plot histogram
    mplstyle.use("seaborn-v0_8-darkgrid")
    plt.figure(figsize=(12, 6))

    # Plot lines
    plt.plot(
        merged_df["month"],
        merged_df["authored_count"],
        label=f"PRs Authored (Total: {total_authored:,})",
        color="skyblue",
        marker="o",
        linewidth=2,
    )
    plt.plot(
        merged_df["month"],
        merged_df["reviewed_count"],
        label=f"PRs Reviewed (Total: {total_reviewed:,})",
        color="lightcoral",
        marker="o",
        linewidth=2,
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
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    # Save the plot
    output_filename = (
        output_path / f"{username}-{repo_owner}-{repo_name}-contribution-histogram.png"
    )
    plt.savefig(output_filename)
    print(f"\nContribution histogram saved as: {output_filename}")


@click.command()
@click.option(
    "--exclude-authored-from-reviewed",
    is_flag=True,
    help="Exclude PRs authored by the user from the reviewed count.",
)
@click.option(
    "--targets",
    required=True,
    help="Target(s) in the format username,owner/repo. Multiple targets can be separated by spaces.",
)
@click.option(
    "--output-dir", default=".", help="Directory to save the output PNG file."
)
def main(exclude_authored_from_reviewed, targets, output_dir):
    """
    CLI entry point for generating contribution histograms.

    Args:
        exclude_authored_from_reviewed (bool): Whether to exclude PRs authored by the user from the reviewed count.
        targets (str): Target(s) in the format username,owner/repo.
        output_dir (str): Directory to save the output PNG file.
    """
    parsed_targets = []
    try:
        target_arr = targets.split(" ")
        for target in target_arr:
            username, repo = target.split(",")
            repo_owner, repo_name = repo.split("/")
            parsed_targets.append((username, repo_owner, repo_name))
    except ValueError as e:
        raise click.BadParameter(
            f"Error parsing target '{targets}': {str(e)}. Expected format: username,owner/repo"
        )

    for target in parsed_targets:
        try:
            generate_contribution_histogram(
                target[0],
                target[1],
                target[2],
                output_dir,
                exclude_authored_from_reviewed,
            )
        except Exception as e:
            click.echo(
                f"Error generating histogram for {target[0]} in {target[1]}/{target[2]}: {str(e)}",
                err=True,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
