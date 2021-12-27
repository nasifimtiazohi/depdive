import re
from version_differ.version_differ import FileDiff
from package_locator.locator import get_repository_url_and_subdir
from depdive.common import LineDelta, process_whitespace
from depdive.registry_diff import get_registry_version_diff
from depdive.repository_diff import (
    RepositoryDiff,
    SingleCommitFileChangeData,
    get_full_file_history,
)


class UncertainSubdir(Exception):
    """Cannot verify package directory at version commit"""

    pass


class LineCounterCommit:
    def __init__(self, commit: str):
        self.commit: str = commit
        self.file: str = None
        self.change: LineDelta = None


class LineCounter:
    def __init__(self, line: str):
        self.line: str = line
        self.registry_diff: LineDelta = None  # AddDelData
        self.mapped_commits: dict[str, LineCounterCommit] = {}  # each commit key maps to repo_file_name and
        self.registry_diff_error: LineDelta = None


class FileCodeToCommitMap:
    def __init__(self, file):
        self.file = file
        self.line_counter: dict[str, LineCounter] = {}


class CodeReviewAnalysis:
    def __init__(self, ecosystem, package, old_version, new_version, repository=None, directory=None):
        self.ecosystem: str = ecosystem
        self.package: str = package
        self.old_version: str = old_version
        self.new_version: str = new_version

        self.repository: str = repository
        self.directory: str = directory
        if not self.repository:
            self._locate_repository()

        # this fields will be updated after analysis is run.
        # Is this a good design pattern?
        self.start_commit: str = None
        self.end_commit: str = None
        self.code_to_commit_map: dict[str, FileCodeToCommitMap] = {}
        self.phantom_files: dict[str, FileDiff] = {}
        # files present in repo but contains lines
        # that are only present in registry
        self.phantom_lines: dict[str, dict[str, LineDelta]] = {}

    def _locate_repository(self):
        self.repository, self.directory = get_repository_url_and_subdir(self.ecosystem, self.package)

    def get_repo_path_from_registry_path(self, filepath):
        subdir = self.directory.removeprefix("./").removesuffix("/")
        return subdir + "/" + filepath if subdir else filepath

    def _get_phantom_files(self, registry_diff, repository_diff, repo_file_list):
        """
        Phantom files: Files that are present in the registry,
                        but not in the source repository
        """
        phantom_files = {}
        for f in registry_diff.keys():
            repo_f = self.get_repo_path_from_registry_path(f)
            if registry_diff[f].target_file and repo_f not in repo_file_list:
                phantom_files[f] = registry_diff[f]
        return phantom_files

    def _get_phantom_lines_in_a_file(self, registry_file_diff, repo_file_diff):

        p_repo_diff = {}
        for l in repo_file_diff.changed_lines.keys():
            p_l = process_whitespace(l)
            p_repo_diff[p_l] = p_repo_diff.get(p_l, LineDelta())
            p_repo_diff[p_l].add(repo_file_diff.changed_lines[l])

        phantom = {}
        for l in registry_file_diff:
            if l not in p_repo_diff or registry_file_diff[l].delta() != p_repo_diff[l].delta():
                phantom[l] = LineDelta()
                phantom[l].add(registry_file_diff[l])
                if l in p_repo_diff:
                    phantom[l].subtract(p_repo_diff[l])

        return phantom

    def check_package_directory_at_new_version_point(self, subdir):
        if subdir != self.directory:
            if not subdir:
                raise UncertainSubdir
            else:
                self.directory = subdir

    def filter_out_phantom_files(self, registry_diff_data):
        for pf in self.phantom_files.keys():
            registry_diff_data.diff.pop(pf, None)

    def get_registry_file_line_counter(self, f):
        lc = {}
        for l in [process_whitespace(l) for l in f.added_lines]:
            lc[l] = lc.get(l, LineDelta())
            lc[l].additions += 1

        for l in [process_whitespace(l) for l in f.removed_lines]:
            lc[l] = lc.get(l, LineDelta())
            lc[l].deletions += 1

        return lc

    def run_phantom_analysis(self):
        if not self.repository:
            self._locate_repository()

        registry_diff = get_registry_version_diff(self.ecosystem, self.package, self.old_version, self.new_version)
        repository_diff = RepositoryDiff(
            self.ecosystem, self.package, self.repository, self.old_version, self.new_version
        )

        self.check_package_directory_at_new_version_point(repository_diff.new_version_subdir)

        self.phantom_files = self._get_phantom_files(
            registry_diff.diff, repository_diff.diff, repository_diff.new_version_file_list
        )
        self.filter_out_phantom_files(registry_diff)

        for f in registry_diff.diff.keys():
            if not registry_diff.diff[f].target_file:
                continue

            repo_f = self.get_repo_path_from_registry_path(f)

            if not registry_diff.diff[f].source_file and (
                repo_f not in repository_diff.diff.keys() or not repository_diff.diff[repo_f].is_rename
            ):
                # possible explanation: newly included file to be published - get all the commits from the beginning
                repository_diff.diff[repo_f], repository_diff.single_diff[repo_f] = get_full_file_history(
                    repository_diff.repo_path, repo_f, end_commit=repository_diff.new_version_commit
                )

            registry_file_diff = self.get_registry_file_line_counter(registry_diff.diff[f])

            phantom_lines = self._get_phantom_lines_in_a_file(
                registry_file_diff, repository_diff.single_diff.get(repo_f, SingleCommitFileChangeData())
            )

            if phantom_lines:

                # Case 2: try looking beyond the initial commit boundary
                has_commit_boundary_changed = repository_diff.check_beyond_commit_boundary(
                    repo_f,
                    phantom_lines,
                )

                if has_commit_boundary_changed:
                    phantom_lines = self._get_phantom_lines_in_a_file(
                        registry_file_diff, repository_diff.single_diff.get(repo_f, SingleCommitFileChangeData())
                    )

            if phantom_lines:
                self.phantom_lines[f] = phantom_lines

        self.start_commit = repository_diff.old_version_commit
        self.end_commit = repository_diff.new_version_commit
