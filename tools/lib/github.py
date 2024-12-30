#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright © 2024 The TokTok team
import os
import re
from functools import cache as memoize
from typing import Any
from typing import Optional

import requests
from lib import git


@memoize
def github_token() -> Optional[str]:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        print("Authorization with GITHUB_TOKEN")
    else:
        print("Unauthorized (low rate limit applies)")
        print("Set GITHUB_TOKEN to increase the rate limit")
    return token


def auth_headers(required: bool) -> dict[str, str]:
    """Get the authentication headers for GitHub.

    If the GITHUB_TOKEN environment variable is not set, this function will
    raise an error if required is True, or return an empty dictionary if
    required is False.
    """
    token = github_token()
    if not token:
        if required:
            raise ValueError("GITHUB_TOKEN is needed to upload tarballs")
        else:
            return {}
    return {"Authorization": f"token {token}"}


api_requests: list[str] = []


def api_url() -> str:
    return os.getenv("GITHUB_API_URL") or "https://api.github.com"


def api_uncached(url: str, auth: bool, params: tuple[tuple[str, str],
                                                     ...]) -> Any:
    """Call the GitHub API with the given URL (GET only).

    Not cached, use the api() function to cache calls.
    """
    api_requests.append(f"GET {api_url()}{url}")
    response = requests.get(
        f"{api_url()}{url}",
        headers=auth_headers(required=auth),
        params=dict(params),
    )
    response.raise_for_status()
    return response.json()


@memoize
def api(
        url: str,
        auth: bool = False,
        params: tuple[tuple[str, str], ...] = tuple(),
) -> Any:
    """Cache-calls the GitHub API with the given URL (GET only).

    Authorization is done with the GITHUB_TOKEN environment variable if it is set.

    Args:
        url: The URL to call, starting with a slash.
        auth: Whether authorization is required (will raise an exception if no token is available).
        params: A list of key-value pairs to pass as query parameters.
    """
    return api_uncached(url, auth, params)


@memoize
def release_id(tag: str) -> int:
    """Get the GitHub release ID number for a tag."""
    slug = git.remote_slug("upstream")
    response = requests.get(
        f"https://api.github.com/repos/{slug}/releases/tags/{tag}",
        headers=auth_headers(False),
    )
    response.raise_for_status()
    return int(response.json()["id"])


def head_ref() -> str:
    """Calls git rev-parse --abbrev-ref HEAD to get the current branch name."""
    return os.getenv("GITHUB_HEAD_REF") or git.current_branch()


def actor() -> str:
    """Returns the GitHub username for the current repository."""
    return os.getenv("GITHUB_ACTOR") or git.remote_slug("origin").name


def repository() -> str:
    return os.getenv("GITHUB_REPOSITORY") or str(git.remote_slug("upstream"))


def pr_number() -> int:
    """Calls the GitHub API to get the PR number for the current branch.

    Requires the GITHUB_API_URL and GITHUB_REF environment variables to be set.
    """
    return int(
        api(
            f"/repos/{repository()}/pulls",
            (("head", f"{actor()}:{head_ref()}"), ),
        )[0]["number"])


def ref_name() -> str:
    return os.getenv("GITHUB_REF_NAME") or f"{pr_number()}/merge"


def pr() -> Any:
    """Calls the GitHub API to get the current PR object."""
    return api(f"/repos/{repository()}/pulls/{ref_name().split('/')[0]}")


def pr_branch() -> str:
    """Calls the GitHub API to get the branch name for the current PR."""
    return str(pr()["head"]["ref"])


def base_ref() -> str:
    """Calls the GitHub API to get the base branch for the current PR."""
    return os.getenv("GITHUB_BASE_REF") or str(pr()["base"]["ref"])


def base_branch() -> str:
    """Get the base ref with its remote path."""
    remotes = git.remotes()
    if "upstream" in remotes:
        return f"upstream/{base_ref()}"
    elif "origin" in remotes:
        return f"origin/{base_ref()}"
    raise ValueError("No upstream or origin remotes found")


def milestones() -> list[str]:
    """Get the names of all milestones in the repository."""
    return [m["title"] for m in api(f"/repos/{repository()}/milestones")]


def next_release() -> str:
    """Get the next release number (based on the smallest open milestone).

    Milestones are formatted like v1.18.0 or v1.18.x (ignored). The next
    release number is the smallest version number in the milestones list.
    """
    return min(
        (m for m in milestones() if re.match(r"v\d+\.\d+\.\d+$", m)),
        key=lambda m: tuple(map(int, m[1:].split("."))),
    )


def prereleases(version: str) -> list[str]:
    """Get the names of all prereleases for a given version in the repository."""
    return [
        r["tag_name"] for r in api(f"/repos/{repository()}/releases")
        if f"{version}-rc." in r["tag_name"]
    ]


def release_candidates(version: str) -> list[int]:
    """Get the RC numbers (the number after "-rc.") for prereleases of a given version."""
    return [
        int(i) for r in prereleases(version)
        for i in re.findall(r"-rc\.(\d+)$", r)
    ]
