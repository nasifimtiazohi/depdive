from depdive.repository_diff import *
import tempfile
from git import Repo


def get_repository_diff_stats(diff):
    files = len(diff)
    lines = additions = deletions = 0
    commits = set()
    for f in diff.keys():
        for l in diff[f].keys():
            lines += 1
            for c in diff[f][l].keys():
                commits.add(c)
                additions += diff[f][l][c].additions
                deletions += diff[f][l][c].deletions
    return len(commits), files, lines, additions, deletions


def test_repository_diff():
    assert get_repository_diff_stats(
        get_repository_diff("tokio", "https://github.com/tokio-rs/tokio", "1.8.4", "1.9.0").diff
    ) == (53, 93, 4523, 4646, 2562)

    assert get_repository_diff_stats(
        get_repository_diff(
            "package-locator", "https://github.com/nasifimtiazohi/package-locator", "0.4.0", "0.4.1"
        ).diff
    ) == (2, 10, 182, 102, 120)


def test_repository_file_list():
    repository = "https://github.com/nasifimtiazohi/package-locator"
    commit = "8ba11d8904971c53e9a7fe6522ed148a3b9e6c45"

    with tempfile.TemporaryDirectory() as temp_dir:
        Repo.clone_from(repository, temp_dir)
        files = get_repository_file_list(temp_dir, commit)
        assert len(files) == 82
        assert "package_locator/locator.py" not in files
