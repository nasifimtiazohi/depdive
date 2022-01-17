from curses import meta
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


class GitError(Exception):
    pass


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


def get_doubledot_inbetween_commits(repo_path, commit_a, commit_b=""):
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
    """
    we do not use git show to get diffs from merge commit
    """
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
    """
    we do not use git show to get diffs from merge commit
    """
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
                files[file].commits.add(commit)
                files[file].changed_lines[line][commit] = diff[file].changed_lines[line]

    def recurring_merge_rename(f, merged_files):
        merged_files.add(f)
        if files[f].is_rename and files[f].old_name in files.keys() and files[f].old_name not in merged_files:
            old_f = files[f].old_name
            files[old_f] = recurring_merge_rename(old_f, merged_files)
            for l in files[old_f].changed_lines.keys():
                if l not in files[f].changed_lines:
                    files[f].changed_lines[l] = files[old_f].changed_lines[l]
                else:
                    for c in files[old_f].changed_lines[l]:
                        if c not in files[f].changed_lines[l]:
                            files[f].changed_lines[l][c] = files[old_f].changed_lines[l][c]
            files[f].commits |= files[old_f].commits
        return files[f]

    # converge with old name in the case of renamed files
    for f in files.keys():
        files[f] = recurring_merge_rename(f, set())

    def get_all_old_names(f, merged_files):
        merged_files.add(f)
        if f not in files or not files[f].is_rename or files[f].old_name in merged_files:
            return []
        else:
            return [files[f].old_name] + get_all_old_names(files[f].old_name, merged_files)

    rename_map = {}
    all_old_names = set()
    for f in files.keys():
        rename_map[f] = set(get_all_old_names(f, set()))
        all_old_names |= rename_map[f]

    for f in list(files.keys()):
        if f not in all_old_names and rename_map[f]:
            for old_f in rename_map[f]:
                files[old_f] = files[f]

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


def is_same_commit(sha_a, sha_b):
    return sha_a.startswith(sha_b) or sha_b.startswith(sha_a)


def git_blame_delete(repo_path, filepath, start_commit, new_version_commit, repo_diff):
    filelines = get_file_lines(repo_path, start_commit, filepath)

    p_repo_diff = {}
    for l in repo_diff.changed_lines.keys():
        p_l = process_whitespace(l)
        p_repo_diff[p_l] = p_repo_diff.get(p_l, {})
        for c in repo_diff.changed_lines[l].keys():
            p_repo_diff[p_l][c] = p_repo_diff[p_l].get(c, LineDelta())
            p_repo_diff[p_l][c].add(repo_diff.changed_lines[l][c])

    cmd = "cd {path};git blame --reverse -l {start_commit}..{end_commit} {fname}".format(
        path=repo_path, start_commit=start_commit, end_commit=new_version_commit, fname=filepath
    )
    with os.popen(cmd) as process:
        blame = process.readlines()
    assert len(blame) == len(filelines)

    blame = [line.split(" ")[0] for line in blame]
    blame = [line.removeprefix("^") for line in blame]

    blame_map = defaultdict(list)
    for i, c in enumerate(blame):
        blame_map[c] += [i]

    def find_removal_commit(line, candidate_commits):
        """
        git blame may be inaccurate in case of some bulk changes,
        so run a validation step,
        by checking if the commit has indeed deleted the line

        assumption: commits are sorted old to new
        TODO: do explicit sorting within the function, maybe not because inner function
        """
        p_l = process_whitespace(line)
        if p_l in p_repo_diff.keys():
            for commit in candidate_commits:
                if commit in p_repo_diff[p_l].keys() and p_repo_diff[p_l][commit].deletions > 0:
                    return commit

    c2c = defaultdict(list)
    for commit in blame_map.keys():
        assert commit.isalnum()
        if is_same_commit(commit, new_version_commit):
            continue

        next_commits = get_doubledot_inbetween_commits(repo_path, commit, new_version_commit)[::-1]
        for i in blame_map[commit]:
            line = process_whitespace(filelines[i])
            next_commit = find_removal_commit(line, next_commits)
            if next_commit:
                c2c[next_commit] += [filelines[i]]
            else:
                # possible explanations
                # 1. blank line
                # 2. deletion commit present in both old_version_commit and new_version_commit
                # 3. line present in new version, git blame error due to bulk change somewhere
                pass
    return c2c


def get_common_ancestor(repo_path, start_commit, end_commit):
    try:
        cmd = "cd {path};git rev-parse $(git log --pretty=%H {start_commit}..{end_commit} | tail -1)^".format(
            path=repo_path, start_commit=start_commit, end_commit=end_commit
        )
        with os.popen(cmd) as process:
            lines = process.readlines()

        assert len(lines) == 1
        ca = lines[0].strip()
        assert ca.isalnum()

        return ca
    except:
        raise GitError


def valid_commit(repo_path, commit):
    repo = Repo(repo_path)
    try:
        repo.commit(commit)
        return True
    except:
        return False


class RepositoryDiff:
    def __init__(
        self, ecosystem, package, repository, old_version, new_version, old_version_commit=None, new_version_commit=None
    ):
        self.ecosystem = ecosystem
        self.package = package
        self.repository = repository
        self.old_version = old_version
        self.new_version = new_version

        self._temp_dir = None
        self.repo_path = None

        self.old_version_commit = old_version_commit
        self.new_version_commit = new_version_commit

        self.old_version_subdir = None  # package directory at the old version commit
        self.new_version_subdir = None  # package directory at the new version commit
        self.common_ancestor_commit_new_and_old_version = None

        self.commits = None
        self.reverse_commits = None

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

    def cleanup(self):
        self._temp_dir.cleanup()

    def build_repository_diff(self):
        if not self.repo_path:
            self._temp_dir = tempfile.TemporaryDirectory()
            self.repo_path = self._temp_dir.name
            Repo.clone_from(self.repository, self.repo_path)

        if (
            not self.old_version_commit
            or not self.new_version_commit
            or not valid_commit(self.repo_path, self.old_version_commit)
            or not valid_commit(self.repo_path, self.new_version_commit)
        ):
            self.old_version_commit = self.get_commit_of_release(self.old_version)
            self.new_version_commit = self.get_commit_of_release(self.new_version)

            if not self.old_version_commit or not self.new_version_commit:
                raise ReleaseCommitNotFound

        self.common_ancestor_commit_new_and_old_version = get_common_ancestor(
            self.repo_path, self.old_version_commit, self.new_version_commit
        )

        self.commits = set(
            get_doubledot_inbetween_commits(self.repo_path, self.old_version_commit, self.new_version_commit)
        )
        self.reverse_commits = set(
            get_doubledot_inbetween_commits(self.repo_path, self.new_version_commit, self.old_version_commit)
        )
        self.diff = get_commit_diff_stats_from_repo(self.repo_path, list(self.commits), list(self.reverse_commits))

        self.new_version_file_list = get_repository_file_list(self.repo_path, self.new_version_commit)

        try:
            self.old_version_subdir = locate_subdir(
                self.ecosystem, self.package, self.repository, commit=self.old_version_commit, version=self.old_version
            )
            self.new_version_subdir = locate_subdir(
                self.ecosystem, self.package, self.repository, commit=self.new_version_commit, version=self.new_version
            )
        except:
            self._temp_dir.cleanup()
            raise UncertainSubdir

        self.single_diff = get_diff_files(
            get_inbetween_commit_diff(self.repo_path, self.old_version_commit, self.new_version_commit)
        )

    def get_full_file_history(self, filepath, end_commit="HEAD"):
        """ get commit history of filepath upto given commit point """
        commits = get_all_commits_on_file(self.repo_path, filepath, end_commit=end_commit)
        self.commits |= set(commits)

        diff_commit_mapping = get_commit_diff_stats_from_repo(self.repo_path, commits)

        single_diff = SingleCommitFileChangeData(filepath)
        lines = get_file_lines(self.repo_path, end_commit, filepath)
        for l in lines:
            single_diff.changed_lines[l] = single_diff.changed_lines.get(l, LineDelta())
            single_diff.changed_lines[l].additions += 1

        self.diff[filepath] = diff_commit_mapping[filepath]
        self.single_diff[filepath] = single_diff

    def traverse_beyond_new_version_commit(self, filepath, phantom_lines):
        """
        returns new possible commit boundary
        for the corner case where the version was wrongly tagged at some commit
        and the actual uploaded artifact contains one or more commits beyond
        the boundary pointed at by the version tag

        Note that, we expand our commit boundary very conservatively,
        if the immediate next commit outside the boundary on the given file
        does not address phantom lines, we quit.

        We only do it for the new version commit,
        as old version does not affect phantom lines present in the new update.

        Also, if commit boundary has changed, we re-process the object
        """

        new_version_commit, old_version_commit = self.new_version_commit, self.old_version_commit
        if not new_version_commit or not old_version_commit:
            return False

        # check if there's any phantom addition
        additions = 0
        for l in phantom_lines.keys():
            additions += phantom_lines[l].additions
        if additions == 0:
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
                            if phantom_lines[p_line].additions == 0:
                                phantom_lines.pop(p_line)
                            new_version_commit = commit
                            commit_outside_boundary = False
                if commit_outside_boundary or not phantom_lines:
                    break

        if new_version_commit != self.new_version_commit or old_version_commit != self.old_version_commit:
            # get new version commit
            # however, the next commit can be from another branch
            # was merged with cur new version commit afterwards
            # if that's the case we want the merge commit
            after_commits = get_doubledot_inbetween_commits(self.repo_path, new_version_commit)[::-1]
            if self.new_version_commit not in after_commits:
                self.new_version_commit = new_version_commit
            else:
                idx = after_commits.index(self.new_version_commit)
                if idx < len(after_commits) - 1:
                    self.new_version_commit = after_commits[idx + 1]
                else:
                    assert (False, "check commit boundary checking")

            self.build_repository_diff()
            return True

        return False
