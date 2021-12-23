from git import Repo
from unidiff import PatchSet
from version_differ.version_differ import get_commit_of_release
import tempfile
from os.path import join, relpath
import os
from package_locator.directory import locate_subdir
from depdive.common import LineDelta, process_whitespace


class ReleaseCommitNotFound(Exception):
    def message():
        return "Release commit not found"


class SingleCommitFileChangeData:
    def __init__(self):
        self.source_file: str = None
        self.target_file: str = None
        self.is_rename: bool = False
        # each line points to adddel data
        self.changed_lines: dict[str, LineDelta] = {}


class MultipleCommitFileChangeData:
    def __init__(self, filename):
        self.filename: str = filename
        # keeps track if it is a renamed file
        self.is_rename: bool = False
        self.old_name: str = None
        # each line points to a commit and adddel data
        self.changed_lines: dict[str, dict[str, LineDelta]] = {}


class RepositoryDiff:
    def __init__(self, package, repository, old_version, new_version):
        self.package = package
        self.repository = repository
        self.old_version = old_version
        self.new_version = new_version

        self.old_version_commit = None
        self.new_version_commit = None
        self.diff = None  # diff across individual commits
        self.new_version_file_list = None
        self.new_version_subdir = None  # package directory at the new version commit
        self.single_diff = None  # single diff from old to new


def get_doubeledot_inbetween_commits(repo_path, commit_a, commit_b):
    repo = Repo(repo_path)
    commits = repo.iter_commits("{}..{}".format(commit_a, commit_b))
    return [str(c) for c in commits]


def get_all_commits_on_file(repo_path, filepath, start_commit=None, end_commit=None):
    # upto given commit
    repo = Repo(repo_path)

    if start_commit and end_commit:
        commits = repo.git.log(
            "{}^..{}".format(start_commit, end_commit), "--pretty=%H", "--follow", "--", filepath
        ).split("\n")
    elif start_commit:
        commits = repo.git.log("{}^..".format(start_commit), "--pretty=%H", "--follow", "--", filepath).split("\n")
    elif end_commit:
        commits = repo.git.log(end_commit, "--pretty=%H", "--follow", "--", filepath).split("\n")
    else:
        commits = repo.git.log("--pretty=%H", "--follow", "--", filepath).split("\n")

    return [c for c in commits if c]


def get_commit_diff(repo_path, commit, reverse=False):
    repo = Repo(repo_path)
    try:
        if not reverse:
            uni_diff_text = repo.git.diff(
                "{}~".format(commit), "{}".format(commit), ignore_blank_lines=True, ignore_space_at_eol=True
            )
        else:
            uni_diff_text = repo.git.diff(
                "{}".format(commit), "{}~".format(commit), ignore_blank_lines=True, ignore_space_at_eol=True
            )
    except:
        # in case of first commit, no parent
        uni_diff_text = repo.git.show("{}".format(commit), ignore_blank_lines=True, ignore_space_at_eol=True)

    return uni_diff_text


def get_commit_diff_for_file(repo_path, filepath, commit, reverse=False):
    repo = Repo(repo_path)
    try:
        if not reverse:
            uni_diff_text = repo.git.diff(
                "{}~".format(commit),
                "{}".format(commit),
                "--",
                filepath,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            )
        else:
            uni_diff_text = repo.git.diff(
                "{}".format(commit),
                "{}~".format(commit),
                "--",
                filepath,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            )
    except:
        # in case of first commit, no parent
        uni_diff_text = repo.git.show(
            "{}".format(commit), "--", filepath, ignore_blank_lines=True, ignore_space_at_eol=True
        )

    return uni_diff_text


def get_inbetween_commit_diff(repo_path, commit_a, commit_b):
    assert commit_a != commit_b  # assumption

    repo = Repo(repo_path)
    uni_diff_text = repo.git.diff(
        "{}".format(commit_a), "{}".format(commit_b), ignore_blank_lines=True, ignore_space_at_eol=True
    )
    return uni_diff_text


def get_inbetween_commit_diff_for_file(repo_path, filepath, commit_a, commit_b):
    assert commit_a != commit_b  # assumption

    repo = Repo(repo_path)
    uni_diff_text = repo.git.diff(
        "{}".format(commit_a),
        "{}".format(commit_b),
        "--",
        filepath,
        ignore_blank_lines=True,
        ignore_space_at_eol=True,
    )
    return uni_diff_text


def process_patch_filepath(filepath):
    filepath = filepath.removeprefix("a/")
    filepath = filepath.removeprefix("b/")
    if filepath == "/dev/null":
        filepath = None
    return filepath


def get_diff_files(uni_diff_text):
    patch_set = PatchSet(uni_diff_text)
    files = {}

    for patched_file in patch_set:
        f = SingleCommitFileChangeData()
        f.source_file = process_patch_filepath(patched_file.source_file)
        f.target_file = process_patch_filepath(patched_file.target_file)
        f.is_rename = patched_file.is_rename

        add_lines = [line.value for hunk in patched_file for line in hunk if line.is_added and line.value.strip()]

        del_lines = [line.value for hunk in patched_file for line in hunk if line.is_removed and line.value.strip()]

        for line in del_lines:
            f.changed_lines[line] = f.changed_lines.get(line, LineDelta())
            f.changed_lines[line].deletions += 1

        for line in add_lines:
            f.changed_lines[line] = f.changed_lines.get(line, LineDelta())
            f.changed_lines[line].additions += 1

        files[patched_file.path] = f

    return files


def get_commit_diff_stats_from_repo(repo_path, commits, reverse_commits=[]):
    files = {}

    for commit in commits + reverse_commits:
        diff = get_diff_files(get_commit_diff(repo_path, commit, reverse=commit in reverse_commits))
        for file in diff.keys():
            files[file] = files.get(file, MultipleCommitFileChangeData(file))

            if diff[file].is_rename:
                files[file].is_rename = True
                files[file].old_name = diff[file].source_file

            for line in diff[file].changed_lines.keys():
                files[file].changed_lines[line] = files[file].changed_lines.get(line, {})
                assert commit not in files[file].changed_lines[line]
                files[file].changed_lines[line][commit] = diff[file].changed_lines[line]

    def recurring_merge_rename(f):
        if files[f].is_rename and files[f].old_name in files.keys():
            old_f = files[f].old_name
            files[old_f] = recurring_merge_rename(old_f)
            for l in files[old_f].changed_lines.keys():
                if l not in files[f].changed_lines:
                    files[f].changed_lines[l] = files[old_f].changed_lines[l]
                else:
                    for c in files[old_f].changed_lines[l]:
                        if c not in files[f].changed_lines[l]:
                            files[f].changed_lines[l][c] = files[old_f].changed_lines[l][c]
        return files[f]

    # converge with old name in the case of renamed files
    for f in files.keys():
        files[f] = recurring_merge_rename(f)

    return files


def get_diff_file_commit_mapping(path, old_commit, new_commit):
    commits = get_doubeledot_inbetween_commits(path, old_commit, new_commit)
    reverse_commits = get_doubeledot_inbetween_commits(path, new_commit, old_commit)
    diff_file_commit_mapping = get_commit_diff_stats_from_repo(path, commits, reverse_commits)
    return diff_file_commit_mapping


def get_repository_file_list(repo_path, commit):
    repo = Repo(repo_path)
    head = repo.head.object.hexsha

    repo.git.checkout(commit)
    filelist = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            filelist.append(relpath(join(root, file), repo_path))
    repo.git.checkout(head)

    return set(filelist)


def get_repository_diff(ecosystem, package, repository, old_version, new_version, old_commit=None, new_commit=None):
    data = RepositoryDiff(package, repository, old_version, new_version)

    with tempfile.TemporaryDirectory() as repo_path:
        repo = Repo.clone_from(repository, repo_path)

        if not old_commit or not new_commit:
            tags = repo.tags

            if not old_commit:
                old_commit = str(get_commit_of_release(tags, package, old_version))
            if not new_commit:
                new_commit = str(get_commit_of_release(tags, package, new_version))

            if not old_commit or not new_commit:
                raise ReleaseCommitNotFound

        data.old_version_commit, data.new_version_commit = old_commit, new_commit
        data.diff = get_diff_file_commit_mapping(repo_path, old_commit, new_commit)
        data.new_version_file_list = get_repository_file_list(repo_path, new_commit)
        data.new_version_subdir = locate_subdir(ecosystem, package, repository, new_commit)
        data.single_diff = get_diff_files(get_inbetween_commit_diff(repo_path, old_commit, new_commit))

    return data


def get_file_history(repository, filepath, start_commit=None, end_commit=None):
    """ get commit history of filepath upto given commit point """
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)
        commits = get_all_commits_on_file(repo_path, filepath, start_commit=start_commit, end_commit=end_commit)

        diff_commit_mapping = get_commit_diff_stats_from_repo(repo_path, commits)
        if len(commits) > 1:
            single_diff = get_diff_files(
                get_inbetween_commit_diff_for_file(repo_path, filepath, commits[-1], commits[0])
            )
        else:
            single_diff = get_diff_files(get_commit_diff_for_file(repo_path, filepath, commits[0]))

        return diff_commit_mapping[filepath], single_diff[filepath]


def check_commits_beyond_version_tags(repository, old_version_commit, new_version_commit, filepath, phantom_lines):
    """
    returns new possible commit boundary
    for the corner case where the version was wrongly tagged at some commit
    and the actual uploaded artifact contains one or more commits beyond
    the boundary pointed at by the version tag

    Note that, we expand our commit boundary very conservatively,
    if the immediate next commit outside the boundary on the fiven file
    does not address phantom lines, we quit.
    """
    with tempfile.TemporaryDirectory() as repo_path:
        Repo.clone_from(repository, repo_path)

        # first take a look at the commis afterward new_version_commits
        commits = get_all_commits_on_file(repo_path, filepath, start_commit=new_version_commit)[::-1]
        commits = commits[1:] if commits[0] == new_version_commit else commits
        for commit in commits:
            print(commit)
            diff = get_diff_files(get_commit_diff(repo_path, commit))
            commit_outside_boundary = True  # assume this commit is outside the actual boundary
            if filepath in diff:
                commit_diff = diff[filepath].changed_lines
                for line in commit_diff.keys():
                    p_line = process_whitespace(line)
                    if p_line in phantom_lines.keys():
                        phantom_lines[p_line].subtract(commit_diff[line])
                        if phantom_lines[p_line].empty():
                            phantom_lines.pop(p_line)
                        new_version_commit = commit
                        commit_outside_boundary = False

            if commit_outside_boundary or not phantom_lines:
                break

        commits = get_all_commits_on_file(repo_path, filepath, end_commit=old_version_commit)
        commits = commits[1:] if commits[0] == old_version_commit else commits
        for commit in commits:
            diff = get_diff_files(get_commit_diff(repo_path, commit))
            commit_outside_boundary = True  # assume this commit is outside the actual boundary
            if filepath in diff:
                commit_diff = diff[filepath].changed_lines
                for line in commit_diff.keys():
                    p_line = process_whitespace(line)
                    if p_line in phantom_lines.keys():
                        phantom_lines[p_line].subtract(commit_diff[line])
                        if phantom_lines[p_line].empty():
                            phantom_lines.pop(p_line)
                        old_version_commit = commit
                        commit_outside_boundary = False

            if commit_outside_boundary or not phantom_lines:
                break

        return old_version_commit, new_version_commit


def get_file_lines(repository, commit, filepath):
    with tempfile.TemporaryDirectory() as repo_path:
        repo = Repo.clone_from(repository, repo_path)
        head = repo.head.object.hexsha

        repo.git.checkout(commit)
        with open(join(repo_path, filepath), "r") as f:
            lines = f.readlines()
        repo.git.checkout(head)

        return lines


def same_file_content(file_a_lines, file_b_lines):
    a = [process_whitespace(x) for x in file_a_lines]
    a = [x for x in a if x]

    b = [process_whitespace(x) for x in file_b_lines]
    b = [x for x in b if x]

    return a == b
