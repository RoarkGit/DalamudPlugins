"""Set each plugin's DownloadCount in pluginmaster.json to its total latest.zip release downloads.

Dalamud shows DownloadCount next to the author in the plugin installer, but nothing reports
installs back to a custom repo, so this reads GitHub's own per-asset download counts instead.
The count covers every release, so it doesn't reset when a new version ships.

Usage: python scripts/update_download_counts.py [path/to/pluginmaster.json]
Set GH_TOKEN to raise the API rate limit; it isn't needed to read public releases.
"""

import json
import os
import re
import sys
import urllib.request

ASSET_NAME = "latest.zip"


def github_get(url):
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def total_downloads(repo):
    total = 0
    page = 1
    while True:
        releases = github_get(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}")
        for release in releases:
            total += sum(a["download_count"] for a in release["assets"] if a["name"] == ASSET_NAME)
        if len(releases) < 100:
            return total
        page += 1


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "pluginmaster.json"
    with open(path) as f:
        plugins = json.load(f)

    changed = False
    for plugin in plugins:
        match = re.match(r"https://github\.com/([^/]+/[^/]+?)/?$", plugin.get("RepoUrl", ""))
        if not match:
            print(f"{plugin['InternalName']}: no GitHub RepoUrl, skipping")
            continue

        count = total_downloads(match.group(1))
        if plugin.get("DownloadCount") != count:
            print(f"{plugin['InternalName']}: {plugin.get('DownloadCount')} -> {count}")
            plugin["DownloadCount"] = count
            changed = True
        else:
            print(f"{plugin['InternalName']}: {count} (unchanged)")

    if changed:
        with open(path, "w") as f:
            json.dump(plugins, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
