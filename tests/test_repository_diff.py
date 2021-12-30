from depdive.repository_diff import *
from package_locator.common import CARGO, PYPI
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
        RepositoryDiff(CARGO, "tokio", "https://github.com/tokio-rs/tokio", "1.8.4", "1.9.0").diff
    ) == (53, 92, 4376, 3733, 3015)

    assert get_repository_diff_stats(
        RepositoryDiff(
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
        diff_commit_mapping = get_full_file_history(repo_path, filepath, end_commit=commit)[0]
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
        # TODO check zero

        assert (
            len(
                get_doubeledot_inbetween_commits(
                    repo_path, "95d74cbe8d3df3674dec1445a4608d3288d8b73c", "4d5c4795ad24c326ae16bfe0c39c826c732716a9"
                )
            )
            == 30
        )

        uni_diff_text = get_commit_diff(repo_path, "31fa94208034cb7581a81b06045ff2cf51057b40")
        assert uni_diff_text.split("\n") == [
            "diff --git a/package.json b/package.json",
            "index 822c963..6231a2c 100644",
            "--- a/package.json",
            "+++ b/package.json",
            "@@ -1,6 +1,6 @@",
            " {",
            ' \t"name": "chalk",',
            '-\t"version": "3.0.0",',
            '+\t"version": "4.0.0",',
            ' \t"description": "Terminal string styling done right",',
            ' \t"license": "MIT",',
            ' \t"repository": "chalk/chalk",',
        ]

        uni_diff_text = get_commit_diff(repo_path, "31fa94208034cb7581a81b06045ff2cf51057b40", reverse=True)
        uni_diff_text.split("\n") == [
            "diff --git a/package.json b/package.json",
            "index 6231a2c..822c963 100644",
            "--- a/package.json",
            "+++ b/package.json",
            "@@ -1,6 +1,6 @@",
            " {",
            ' \t"name": "chalk",',
            '-\t"version": "4.0.0",',
            '+\t"version": "3.0.0",',
            ' \t"description": "Terminal string styling done right",',
            ' \t"license": "MIT",',
            ' \t"repository": "chalk/chalk",',
        ]

        uni_diff_text = get_commit_diff_for_file(
            repo_path, ".editorconfig", commit="cffc3552b0853c75f41b92ed2c032988df018442"
        )
        d = get_diff_files(uni_diff_text)
        lines = 0
        for f in d.keys():
            lines += len(d[f].changed_lines.keys())
        assert lines == 10

        uni_diff_text = get_inbetween_commit_diff_for_file(
            repo_path,
            "package.json",
            "89e9e3a5b0601f4eda4c3a92acd887ec836d0175",
            "95d74cbe8d3df3674dec1445a4608d3288d8b73c",
        )
        assert uni_diff_text.split("\n") == [
            "diff --git a/package.json b/package.json",
            "index c2d63f6..47c23f2 100644",
            "--- a/package.json",
            "+++ b/package.json",
            "@@ -1,6 +1,6 @@",
            " {",
            ' \t"name": "chalk",',
            '-\t"version": "4.1.1",',
            '+\t"version": "4.1.2",',
            ' \t"description": "Terminal string styling done right",',
            ' \t"license": "MIT",',
            ' \t"repository": "chalk/chalk",',
        ]

        c2c = git_blame(repo_path, file, end_commit)

        lines = 0
        for c in c2c.keys():
            lines += len(c2c[c])
        assert lines == 32
        assert len(c2c) == 4


def test_repository_git_blame_delete():
    repository = "https://github.com/chalk/chalk"
    end_commit = "4d5c4795ad24c326ae16bfe0c39c826c732716a9"
    start_commit = "31fa94208034cb7581a81b06045ff2cf51057b40"
    file = "package.json"
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)
        c2c = git_blame_delete(repo_path, file, start_commit, end_commit)
        lines = 0
        for c in c2c.keys():
            lines += len(c2c[c])
        assert lines == 24
        assert len(c2c) == 8


def test_repository_common_ancestor():
    repository = "https://github.com/tokio-rs/tokio"
    start_commit = "2273eb1"
    end_commit = "b280c6d"
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)
        assert get_common_start_point(repo_path, start_commit, end_commit) == "677107d8d9278265798c5efdc75374a25b41a4b8"

        get_common_start_point(
            repo_path, "714704253443787cc0c9a395b6d94947bcf26687", start_commit
        ) == "714704253443787cc0c9a395b6d94947bcf26687"


# TODO: get file_commit_stats for rename file
