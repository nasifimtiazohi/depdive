from version_differ.version_differ import FileDiff
from package_locator.locator import get_repository_url_and_subdir
from depdive.common import LineDelta, process_whitespace
from depdive.registry_diff import get_registry_version_diff
from depdive.repository_diff import (
    check_commits_beyond_version_tags,
    get_file_history,
    get_repository_diff,
    get_file_lines,
    same_file_content,
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
            if registry_diff[f].target_file and repo_f not in repository_diff.keys() and repo_f not in repo_file_list:
                phantom_files[f] = registry_diff[f]

        return phantom_files

    def _get_phantom_lines_in_a_file(self, registry_file_diff, repo_commit_diff, repo_single_diff):
        # repo_commit_diff : diff across individual commits
        # single diff from from commmit a to commit b

        p_repo_diff = {}  # processed_repo_diff: total addition and deletion in repo_file
        for line in repo_commit_diff.keys():
            p_line = process_whitespace(line)
            p_repo_diff[p_line] = p_repo_diff.get(p_line, LineDelta())
            for commit in repo_commit_diff[line].keys():
                p_repo_diff[p_line].add(repo_commit_diff[line][commit])

        phantom = {}
        for l in [process_whitespace(l) for l in registry_file_diff.added_lines]:
            if l in p_repo_diff and p_repo_diff[l].additions > 0:
                p_repo_diff[l].additions -= 1
            else:
                phantom[l] = phantom.get(l, LineDelta(0, 0))
                phantom[l].additions += 1

        for l in [process_whitespace(l) for l in registry_file_diff.removed_lines]:
            if l in p_repo_diff and p_repo_diff[l].deletions > 0:
                p_repo_diff[l].deletions -= 1
            else:
                phantom[l] = phantom.get(l, LineDelta(0, 0))
                phantom[l].deletions += 1

        # Case 1:
        # when a line moves around at a great distance
        # due to large changes in close-by
        # git diff detects the line as also changed
        # (deleted here and added there!)
        # Case 2:
        # file renamed somehwere in betweeen
        if phantom and repo_single_diff:
            changed_lines = {process_whitespace(k): v for (k, v) in repo_single_diff.changed_lines.items()}
            for l in list(phantom.keys()):
                if (
                    l in changed_lines
                    and changed_lines[l].additions == phantom[l].additions
                    and changed_lines[l].deletions == phantom[l].deletions
                ):
                    phantom.pop(l)

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

    def map_code_to_commit(self):
        if not self.repository:
            self._locate_repository()

        registry_diff_data = get_registry_version_diff(self.ecosystem, self.package, self.old_version, self.new_version)
        repository_diff_data = get_repository_diff(
            self.ecosystem, self.package, self.repository, self.old_version, self.new_version
        )

        self.check_package_directory_at_new_version_point(repository_diff_data.new_version_subdir)

        self.phantom_files = self._get_phantom_files(
            registry_diff_data.diff, repository_diff_data.diff, repository_diff_data.new_version_file_list
        )
        self.filter_out_phantom_files(registry_diff_data)

        for f in registry_diff_data.diff.keys():
            if not registry_diff_data.diff[f].target_file:
                continue
            repo_f = self.get_repo_path_from_registry_path(f)

            if not registry_diff_data.diff[f].source_file and (
                same_file_content(
                    registry_diff_data.diff[f].added_lines,
                    get_file_lines(self.repository, repository_diff_data.new_version_commit, repo_f),
                )
            ):
                # possible explanation: newly included file to be published - get all the commits from the beginning
                repository_diff_data.diff[repo_f], repository_diff_data.single_diff[repo_f] = get_file_history(
                    self.repository, repo_f, end_commit=repository_diff_data.new_version_commit
                )

            phantom_lines = self._get_phantom_lines_in_a_file(
                registry_diff_data.diff[f],
                repository_diff_data.diff[repo_f].changed_lines if repo_f in repository_diff_data.diff else {},
                repository_diff_data.single_diff[repo_f] if repo_f in repository_diff_data.single_diff else {},
            )

            if phantom_lines:
                # Case 2: try looking beyond the initial commit boundary
                old_commit, new_commit = check_commits_beyond_version_tags(
                    self.repository,
                    repository_diff_data.old_version_commit,
                    repository_diff_data.new_version_commit,
                    repo_f,
                    phantom_lines,
                )

                if (
                    new_commit != repository_diff_data.new_version_commit
                    or old_commit != repository_diff_data.old_version_commit
                ):
                    repository_diff_data = get_repository_diff(
                        self.ecosystem,
                        self.package,
                        self.repository,
                        self.old_version,
                        self.new_version,
                        old_commit,
                        new_commit,
                    )

                phantom_lines = self._get_phantom_lines_in_a_file(
                    registry_diff_data.diff[f],
                    repository_diff_data.diff[repo_f].changed_lines if repo_f in repository_diff_data.diff else {},
                    repository_diff_data.single_diff[repo_f] if repo_f in repository_diff_data.single_diff else {},
                )

            if phantom_lines:
                self.phantom_lines[f] = phantom_lines

        self.start_commit = str(repository_diff_data.old_version_commit)
        self.end_commit = str(repository_diff_data.new_version_commit)
