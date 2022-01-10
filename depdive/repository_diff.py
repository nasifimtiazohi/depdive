from git import Repo
from unidiff import PatchSet
from version_differ.version_differ import get_commit_of_release
import tempfile
from os.path import join, relpath
import os
from package_locator.directory import locate_subdir
from depdive.common import LineDelta, process_whitespace
from collections import defaultdict


class UncertainSubdir(Exception):
    """Cannot verify package directory at version commit"""

    pass


class ReleaseCommitNotFound(Exception):
    def message():
        return "Release commit not found"


class SingleCommitFileChangeData:
    def __init__(self, file=None):
        self.source_file: str = file
        self.target_file: str = file
        self.is_rename: bool = False
        self.changed_lines: dict[str, LineDelta] = {}


class MultipleCommitFileChangeData:
    def __init__(self, filename):
        self.filename: str = filename

        # keeps track if it is a renamed file
        self.is_rename: bool = False
        self.old_name: str = None

        self.commits = set()
        self.changed_lines: dict[str, dict[str, LineDelta]] = {}


def get_doubledot_inbetween_commits(repo_path, commit_a, commit_b):
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
        # Case 1: first commit, no parent
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
    repo = Repo(repo_path)
    uni_diff_text = repo.git.diff(
        "{}".format(commit_a), "{}".format(commit_b), ignore_blank_lines=True, ignore_space_at_eol=True
    )
    return uni_diff_text


def get_inbetween_commit_diff_for_file(repo_path, filepath, commit_a, commit_b):
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

            files[file].commits.add(commit)

    merged_files = set()  # keep track of merged file to avoid infinite recursion

    def recurring_merge_rename(f):
        merged_files.add(f)
        if files[f].is_rename and files[f].old_name in files.keys() and files[f].old_name not in merged_files:

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


def get_repository_file_list(repo_path, commit):
    repo = Repo(repo_path)
    head = repo.head.object.hexsha

    repo.git.checkout(commit, force=True)
    filelist = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            filelist.append(relpath(join(root, file), repo_path))

    repo.git.checkout(head, force=True)
    return set(filelist)


def get_full_file_history(repo_path, filepath, end_commit="HEAD"):
    """ get commit history of filepath upto given commit point """
    commits = get_all_commits_on_file(repo_path, filepath, end_commit=end_commit)

    diff_commit_mapping = get_commit_diff_stats_from_repo(repo_path, commits)

    single_diff = SingleCommitFileChangeData(filepath)
    lines = get_file_lines(repo_path, end_commit, filepath)
    for l in lines:
        single_diff.changed_lines[l] = single_diff.changed_lines.get(l, LineDelta())
        single_diff.changed_lines[l].additions += 1

    return diff_commit_mapping[filepath], single_diff


def get_file_lines(repo_path, commit, filepath):
    repo = Repo(repo_path)
    head = repo.head.object.hexsha

    repo.git.checkout(commit, force=True)
    with open(join(repo_path, filepath), "r") as f:
        lines = f.readlines()

    repo.git.checkout(head, force=True)
    return lines


def git_blame(repo_path, filepath, commit):
    c2c = defaultdict(list)  # commit to code
    repo = Repo(repo_path)
    for commit, lines in repo.blame(commit, filepath):
        c2c[commit.hexsha] += list(lines)
    return c2c


def git_blame_delete(repo_path, filepath, start_commit, end_commit, repo_diff):
    filelines = get_file_lines(repo_path, start_commit, filepath)

    blame = []
    cmd = "cd {path};git blame --reverse -l {start_commit}..{end_commit} {fname}".format(
        path=repo_path, start_commit=start_commit, end_commit=end_commit, fname=filepath
    )
    with os.popen(cmd) as process:
        blame = process.readlines()

    assert len(blame) == len(filelines)

    inbetween_commits = [start_commit] + get_doubledot_inbetween_commits(repo_path, start_commit, end_commit)[::-1]

    def find_commit_idx(commit):
        """
        find index within inbetween commits.
        git can act weird as it can strip some characters in the end for commit sha
        """
        nonlocal inbetween_commits
        for i, c in enumerate(inbetween_commits):
            if c.startswith(commit) or commit.startswith(c):
                return i

    c2c = defaultdict(list)

    def validate_removal_commit(commit, line):
        """
        git blame may be inaccurate in case of some bulk changes,
        so run a validation step,
        by checking if the commit has indeed deleted the line
        """
        for l in repo_diff.changed_lines.keys():
            if process_whitespace(l) == process_whitespace(line):
                if commit in repo_diff.changed_lines[l].keys() and repo_diff.changed_lines[l][commit].deletions > 0:
                    return commit

        for l in repo_diff.changed_lines.keys():
            if process_whitespace(l) == process_whitespace(line):
                for commit in repo_diff.changed_lines[l].keys():
                    if repo_diff.changed_lines[l][commit].deletions > 0:
                        return commit

    for i, line in enumerate(blame):
        commit = line.split(" ")[0]
        commit = commit.removeprefix("^")
        assert not commit.endswith("^") and not commit.endswith("~") and not commit.startswith("~")
        idx = find_commit_idx(commit)
        assert idx is not None
        if idx == len(inbetween_commits) - 1:
            # line still present
            continue

        next_commit = inbetween_commits[idx + 1]
        next_commit = validate_removal_commit(next_commit, filelines[i])
        if next_commit:
            c2c[next_commit] += [filelines[i]]

    return c2c


def get_common_start_point(repo_path, start_commit, end_commit):
    cmd = "cd {path};git rev-parse $(git log --pretty=%H {start_commit}..{end_commit} | tail -1)^".format(
        path=repo_path, start_commit=start_commit, end_commit=end_commit
    )
    with os.popen(cmd) as process:
        lines = process.readlines()
    assert len(lines) == 1
    return lines[0].strip()


class RepositoryDiff:
    def __init__(self, ecosystem, package, repository, old_version, new_version):
        self.ecosystem = ecosystem
        self.package = package
        self.repository = repository
        self.old_version = old_version
        self.new_version = new_version

        self._temp_dir = None
        self.repo_path = None

        self.old_version_commit = None
        self.new_version_commit = None

        self.old_version_subdir = None  # package directory at the old version commit
        self.new_version_subdir = None  # package directory at the new version commit

        self.common_starter_commit = None
        self.diff = None  # diff across individual commits
        self.new_version_file_list = None
        self.single_diff = None  # single diff from old to new

        self.build_repository_diff()

    def get_commit_of_release(self, version):
        repo = Repo(self.repo_path)
        tags = repo.tags
        c = get_commit_of_release(tags, self.package, version)
        if c:
            return c.hexsha

    def build_repository_diff(self):
        if not self.repo_path:
            self._temp_dir = tempfile.TemporaryDirectory()
            self.repo_path = self._temp_dir.name
            Repo.clone_from(self.repository, self.repo_path)

        if not self.old_version_commit or not self.new_version_commit:
            if not self.old_version_commit:
                self.old_version_commit = self.get_commit_of_release(self.old_version)
            if not self.new_version_commit:
                self.new_version_commit = self.get_commit_of_release(self.new_version)

            if not self.old_version_commit or not self.new_version_commit:
                raise ReleaseCommitNotFound

        self.common_starter_commit = get_common_start_point(
            self.repo_path, self.old_version_commit, self.new_version_commit
        )

        self.diff = get_commit_diff_stats_from_repo(
            self.repo_path,
            get_doubledot_inbetween_commits(self.repo_path, self.old_version_commit, self.new_version_commit),
            get_doubledot_inbetween_commits(self.repo_path, self.new_version_commit, self.old_version_commit),
        )

        self.new_version_file_list = get_repository_file_list(self.repo_path, self.new_version_commit)

        try:
            self.old_version_subdir = locate_subdir(
                self.ecosystem, self.package, self.repository, self.old_version_commit
            )
            self.new_version_subdir = locate_subdir(
                self.ecosystem, self.package, self.repository, self.new_version_commit
            )
        except:
            raise UncertainSubdir
        self.single_diff = get_diff_files(
            get_inbetween_commit_diff(self.repo_path, self.old_version_commit, self.new_version_commit)
        )

    def check_beyond_commit_boundary(self, filepath, phantom_lines):
        """
        returns new possible commit boundary
        for the corner case where the version was wrongly tagged at some commit
        and the actual uploaded artifact contains one or more commits beyond
        the boundary pointed at by the version tag

        Note that, we expand our commit boundary very conservatively,
        if the immediate next commit outside the boundary on the fiven file
        does not address phantom lines, we quit.

        Also, if commit boundary has changed, we re-process the object
        """
        new_version_commit, old_version_commit = self.new_version_commit, self.old_version_commit
        if not new_version_commit or not old_version_commit:
            return False

        # first take a look at the commis afterward new_version_commits
        commits = get_all_commits_on_file(self.repo_path, filepath, start_commit=new_version_commit)[::-1]
        if commits:
            commits = commits[1:] if commits[0] == new_version_commit else commits
            for commit in commits:
                diff = get_diff_files(get_commit_diff(self.repo_path, commit))
                commit_outside_boundary = True  # assume this commit is outside the actual boundary
                if filepath in diff:
                    commit_diff = diff[filepath].changed_lines
                    for line in commit_diff.keys():
                        p_line = process_whitespace(line)
                        if p_line in phantom_lines.keys():
                            phantom_lines[p_line].subtract(commit_diff[line])
                            if phantom_lines[p_line].is_empty():
                                phantom_lines.pop(p_line)
                            new_version_commit = commit
                            commit_outside_boundary = False

                if commit_outside_boundary or not phantom_lines:
                    break

        commits = get_all_commits_on_file(self.repo_path, filepath, end_commit=old_version_commit)
        if commits:
            commits = commits[1:] if commits[0] == old_version_commit else commits
            for commit in commits:
                diff = get_diff_files(get_commit_diff(self.repo_path, commit))
                commit_outside_boundary = True  # assume this commit is outside the actual boundary
                if filepath in diff:
                    commit_diff = diff[filepath].changed_lines
                    for line in commit_diff.keys():
                        p_line = process_whitespace(line)
                        if p_line in phantom_lines.keys():
                            phantom_lines[p_line].subtract(commit_diff[line])
                            if phantom_lines[p_line].is_empty():
                                phantom_lines.pop(p_line)
                            old_version_commit = commit
                            commit_outside_boundary = False

                if commit_outside_boundary or not phantom_lines:
                    break

        if new_version_commit != self.new_version_commit or old_version_commit != self.old_version_commit:
            self.new_version_commit, self.old_version_commit = new_version_commit, old_version_commit
            self.build_repository_diff()
            return True
        else:
            return False
