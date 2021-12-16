from git import Repo
from unidiff import PatchSet
from version_differ.version_differ import get_commit_of_release
import tempfile
from os.path import join, relpath
import os


class ReleaseCommitNotFound(Exception):
    pass


class AddDelData:
    def __init__(self, additions=0, deletions=0):
        self.additions = additions
        self.deletions = deletions

    def add(self, other):
        self.additions += other.additions
        self.deletions += other.deletions


class FileChangeData:
    def __init__(self):
        self.source_file = None
        self.target_file = None
        self.is_rename = False
        self.changed_lines = {}


class RepositoryDiff:
    def __init__(self, package, repository, old_version, new_version):
        self.package = package
        self.repository = repository
        self.old_version = old_version
        self.new_version = new_version

        self.old_version_commit = None
        self.new_version_commit = None
        self.diff = None

        self.new_version_file_list = None


def get_inbetween_commits(repo_path, commit_a, commit_b):
    repo = Repo(repo_path)
    commits = repo.iter_commits(str(commit_a) + "..." + str(commit_b))
    return [str(c) for c in commits]


def get_commit_diff(repo_path, commit):
    repo = Repo(repo_path)
    uni_diff_text = repo.git.diff(
        "{}~".format(commit), "{}".format(commit), ignore_blank_lines=True, ignore_space_at_eol=True
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
        f = FileChangeData()
        f.source_file = process_patch_filepath(patched_file.source_file)
        f.target_file = process_patch_filepath(patched_file.target_file)
        f.is_rename = patched_file.is_rename

        add_lines = [line.value for hunk in patched_file for line in hunk if line.is_added and line.value.strip() != ""]

        del_lines = [
            line.value for hunk in patched_file for line in hunk if line.is_removed and line.value.strip() != ""
        ]

        for line in del_lines:
            f.changed_lines[line] = f.changed_lines.get(line, AddDelData())
            f.changed_lines[line].deletions += 1

        for line in add_lines:
            f.changed_lines[line] = f.changed_lines.get(line, AddDelData())
            f.changed_lines[line].additions += 1

        files[patched_file.path] = f
        if f.is_rename:
            # put reverse direction as well
            # to handle diff coming from registry
            files[f.source_file] = f

    return files


def get_commit_diff_stats_from_repo(repo_path, commits):
    files = {}

    for commit in commits:
        diff = get_diff_files(get_commit_diff(repo_path, commit))
        for file in diff.keys():
            files[file] = files.get(file, {})
            for line in diff[file].changed_lines.keys():
                files[file][line] = files[file].get(line, {})
                assert commit not in files[file][line]
                files[file][line][commit] = diff[file].changed_lines[line]
    return files


def get_diff_file_commit_mapping(path, old_commit, new_commit):
    diff_commits = get_inbetween_commits(path, old_commit, new_commit)
    diff_file_commit_mapping = get_commit_diff_stats_from_repo(path, diff_commits)
    return diff_file_commit_mapping


def get_repository_file_list(repo_path, commit):
    repo = Repo(repo_path)
    repo.git.checkout(commit)

    filelist = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            filelist.append(relpath(join(root, file), repo_path))

    return filelist


def get_repository_diff(package, repository, old, new):
    data = RepositoryDiff(package, repository, old, new)
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Repo.clone_from(repository, temp_dir)
        tags = repo.tags

        old_commit = get_commit_of_release(tags, package, old)
        new_commit = get_commit_of_release(tags, package, new)

        if not old_commit or not new_commit:
            raise ReleaseCommitNotFound

        data.old_version_commit, data.new_version_commit = old_commit, new_commit
        data.diff = get_diff_file_commit_mapping(temp_dir, old_commit, new_commit)
        data.new_version_file_list = get_repository_file_list(temp_dir, new_commit)

    return data
