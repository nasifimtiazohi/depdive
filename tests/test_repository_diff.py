from depdive import common
from depdive.repository_diff import *
from package_locator.common import CARGO, NPM, PYPI, COMPOSER, RUBYGEMS
import tempfile
from git import Repo


def get_repository_diff_stats(diff):
    files = len(diff)
    lines = additions = deletions = 0
    commits = set()
    for f in diff.keys():
        for l in diff[f].changed_lines.keys():
            lines += 1
            for c in diff[f].changed_lines[l].keys():
                commits.add(c)
                additions += diff[f].changed_lines[l][c].additions
                deletions += diff[f].changed_lines[l][c].deletions
    return len(commits), files, lines, additions, deletions


def test_repository_diff():
    assert get_repository_diff_stats(
        get_repository_diff(CARGO, "tokio", "https://github.com/tokio-rs/tokio", "1.8.4", "1.9.0").diff
    ) == (53, 92, 4376, 3733, 3015)

    assert get_repository_diff_stats(
        get_repository_diff(
            PYPI, "package-locator", "https://github.com/nasifimtiazohi/package-locator", "0.4.0", "0.4.1"
        ).diff
    ) == (2, 10, 182, 102, 120)


def test_repository_functions():
    repository = "https://github.com/nasifimtiazohi/package-locator"
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)

        commit = "8ba11d8904971c53e9a7fe6522ed148a3b9e6c45"
        filepath = "package_locator/common.py"
        files = get_repository_file_list(repo_path, commit)
        assert len(files) == 82
        assert "package_locator/locator.py" not in files

        commit = "88a6a88c460169ccc904dcf52e9ebb1d09614c68"
        diff_commit_mapping = get_file_history(repo_path, filepath, end_commit=commit)[0]
        commits = set()
        for k in diff_commit_mapping.changed_lines.keys():
            commits |= set(diff_commit_mapping.changed_lines[k].keys())
        assert len(commits) == 10


def test_repository_get_commits():
    repository = "https://github.com/chalk/chalk"
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)

        end_commit = "04fdbd6d8d262ed8668cf3f2e94f647d2bc028d8"
        start_commit = "c25c32a25f4315c1f7ee21cc7b36b497c4f0212a"
        file = "source/utilities.js"

        assert len(get_all_commits_on_file(repo_path, file)) == 7
        assert len(get_all_commits_on_file(repo_path, file, start_commit=start_commit)) == 5
        assert len(get_all_commits_on_file(repo_path, file, end_commit=end_commit)) == 6
        assert len(get_all_commits_on_file(repo_path, file, start_commit=start_commit, end_commit=end_commit)) == 4

        assert (
            len(
                get_doubeledot_inbetween_commits(
                    repo_path, "95d74cbe8d3df3674dec1445a4608d3288d8b73c", "4d5c4795ad24c326ae16bfe0c39c826c732716a9"
                )
            )
            == 30
        )
