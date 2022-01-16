from package_locator.common import NPM
from version_differ.version_differ import FileDiff
from package_locator.locator import get_repository_url_and_subdir
from depdive.common import LineDelta, process_whitespace
from depdive.registry_diff import get_registry_version_diff
from depdive.repository_diff import (
    RepositoryDiff,
    SingleCommitFileChangeData,
    get_full_file_history,
    get_repository_file_list,
    git_blame,
    git_blame_delete,
    UncertainSubdir,
)
from depdive.code_review_checker import CommitReviewInfo


class PackageDirectoryChanged(Exception):
    pass


class DepdiveStats:
    def __init__(
        self,
        reviewed_lines,
        non_reviewed_lines,
        reviewed_commits,
        non_reviewed_commits,
        phantom_files,
        files_with_phantom_lines,
        phantome_lines,
    ) -> None:
        self.reviewed_lines = reviewed_lines
        self.non_reviewed_lines = non_reviewed_lines

        self.total_commit_count = len(reviewed_commits) + len(non_reviewed_commits)
        self.reviewed_commit_count = len(reviewed_commits)

        self.reviewed_commits = reviewed_commits
        self.non_reviewed_commits = non_reviewed_commits

        self.phantom_files = phantom_files
        self.files_with_phantom_lines = files_with_phantom_lines
        self.phantom_lines = phantome_lines

    def print(self):
        print(self.reviewed_commits, self.non_reviewed_commits)
        print(self.phantom_files, self.files_with_phantom_lines, self.phantom_lines)
        print(self.reviewed_lines, self.non_reviewed_lines, self.total_commit_count, self.reviewed_commit_count)


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

        self.start_commit: str = None
        self.end_commit: str = None
        self.common_starter_commit: str = None

        # line counter from version_differ output
        self.registry_diff = {}

        # Newly added phantom files:
        # files present in the registry, but not in repo
        self.phantom_files: set[str] = set()

        # files present in repo,
        # but removed in the new version in the registry
        self.removed_files_in_registry: dict[str, FileDiff] = {}

        # Newly added phantom lines:
        # files present in repo but contains lines
        # that are only present in registry
        self.phantom_lines: dict[str, dict[str, LineDelta]] = {}

        # code to commit mapping
        self.added_loc_to_commit_map: dict[str, dict[str, list(str)]] = {}
        self.removed_loc_to_commit_map: dict[str, dict[str, list(str)]] = {}

        # commit to review map
        self.commit_review_info: dict[str, CommitReviewInfo] = {}

        self.stats: DepdiveStats = None

        self.run_analysis()

    def _locate_repository(self):
        self.repository, self.directory = get_repository_url_and_subdir(self.ecosystem, self.package)

    def get_repo_path_from_registry_path(self, filepath):
        # put custom logic here for specific packages
        if self.ecosystem == NPM and self.package.startswith("@babel") and filepath.startswith("lib/"):
            filepath = "src/" + filepath.removeprefix("lib/")

        subdir = self.directory.removeprefix("./").removesuffix("/")
        return subdir + "/" + filepath if subdir else filepath

    def _process_phantom_files(self, registry_diff, repo_file_list):
        """
        Phantom files: Files that are present in the registry,
                        but not in the source repository

        Also, keep track of files that are present in the repository,
        but have been removed in the new version
        """
        for f in registry_diff.new_version_filelist:
            repo_f = self.get_repo_path_from_registry_path(f)
            if repo_f not in repo_file_list:
                self.phantom_files.add(f)

        for f in registry_diff.diff.keys():
            repo_f = self.get_repo_path_from_registry_path(f)
            if not registry_diff.diff[f].target_file and repo_f in repo_file_list:
                self.removed_files_in_registry[f] = registry_diff.diff[f]

    def _get_phantom_lines_in_a_file(self, registry_file_diff, repo_file_diff):
        p_repo_diff = {}
        for l in repo_file_diff.changed_lines.keys():
            p_l = process_whitespace(l)
            p_repo_diff[p_l] = p_repo_diff.get(p_l, LineDelta())
            p_repo_diff[p_l].add(repo_file_diff.changed_lines[l])

        phantom = {}
        for l in registry_file_diff:
            if l not in p_repo_diff or registry_file_diff[l].delta() != p_repo_diff[l].delta():
                phantom[l] = LineDelta(registry_file_diff[l].additions, registry_file_diff[l].deletions)
                if l in p_repo_diff:
                    phantom[l].subtract(p_repo_diff[l])

        return phantom

    def _get_registry_file_line_counter(self, f):
        lc = {}
        for l in [process_whitespace(l) for l in f.added_lines]:
            lc[l] = lc.get(l, LineDelta())
            lc[l].additions += 1

        for l in [process_whitespace(l) for l in f.removed_lines]:
            lc[l] = lc.get(l, LineDelta())
            lc[l].deletions += 1

        return lc

    def _proccess_phantom_lines(self, registry_diff, repository_diff):
        for f in registry_diff.diff.keys():
            registry_file_diff = self._get_registry_file_line_counter(registry_diff.diff[f])
            self.registry_diff[f] = registry_file_diff

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

            phantom_lines = self._get_phantom_lines_in_a_file(
                registry_file_diff, repository_diff.single_diff.get(repo_f, SingleCommitFileChangeData())
            )

            if phantom_lines:
                # try looking beyond the initial commit boundary
                has_commit_boundary_changed = repository_diff.traverse_beyond_new_version_commit(
                    repo_f,
                    phantom_lines,
                )

                if has_commit_boundary_changed:
                    phantom_lines = self._get_phantom_lines_in_a_file(
                        registry_file_diff, repository_diff.single_diff.get(repo_f, SingleCommitFileChangeData())
                    )

            if phantom_lines:
                self.phantom_lines[f] = phantom_lines

    def _filter_out_phantom_files(self, registry_diff):
        for pf in self.phantom_files:
            registry_diff.diff.pop(pf, None)

        for pf in self.removed_files_in_registry.keys():
            registry_diff.diff.pop(pf, None)

        return registry_diff

    def run_analysis(self):
        if not self.repository:
            self._locate_repository()

        registry_diff = get_registry_version_diff(self.ecosystem, self.package, self.old_version, self.new_version)
        repository_diff = RepositoryDiff(
            self.ecosystem,
            self.package,
            self.repository,
            self.old_version,
            self.new_version,
            old_version_commit=registry_diff.old_version_git_sha,
            new_version_commit=registry_diff.new_version_git_sha,
        )

        # checking package directory
        if repository_diff.old_version_subdir != repository_diff.new_version_subdir:
            raise PackageDirectoryChanged
        elif not repository_diff.new_version_subdir:
            raise UncertainSubdir
        if repository_diff.new_version_subdir != self.directory:
            self.directory = repository_diff.new_version_subdir

        self._process_phantom_files(registry_diff, repository_diff.new_version_file_list)
        self._filter_out_phantom_files(registry_diff)
        self._proccess_phantom_lines(registry_diff, repository_diff)

        self.start_commit = repository_diff.old_version_commit
        self.end_commit = repository_diff.new_version_commit
        self.common_starter_commit = repository_diff.common_starter_commit

        self.map_commit_to_added_lines(repository_diff, registry_diff)
        self.map_commit_to_removed_lines(repository_diff, registry_diff)

        for repo_f in repository_diff.diff.keys():
            for commit in repository_diff.diff[repo_f].commits:
                if commit not in self.commit_review_info:
                    self.commit_review_info[commit] = CommitReviewInfo(self.repository, commit)

        self.stats = self.get_stats()
        repository_diff.cleanup()

    def map_commit_to_added_lines(self, repository_diff, registry_diff):
        files_with_added_lines = set()
        for f in registry_diff.diff.keys():
            if registry_diff.diff[f].target_file:
                files_with_added_lines.add(registry_diff.diff[f].target_file)

        for f in files_with_added_lines:
            repo_f = self.get_repo_path_from_registry_path(f)

            # ignore files with only phantom line changes
            if f in self.phantom_lines.keys() and repo_f not in repository_diff.diff.keys():
                continue

            c2c = git_blame(repository_diff.repo_path, repo_f, repository_diff.new_version_commit)
            for commit in list(c2c.keys()):
                if commit not in repository_diff.commits and commit not in repository_diff.diff[repo_f].commits:
                    c2c.pop(commit)
                else:
                    c2c[commit] = [process_whitespace(l) for l in c2c[commit]]
                    c2c[commit] = [l for l in c2c[commit] if l]

            self.added_loc_to_commit_map[f] = c2c

    def map_commit_to_removed_lines(self, repository_diff, registry_diff):
        starter_point_file_list = get_repository_file_list(
            repository_diff.repo_path, repository_diff.common_starter_commit
        )

        files_with_removed_lines = set()
        for f in registry_diff.diff.keys():
            if registry_diff.diff[f].source_file:
                files_with_removed_lines.add(registry_diff.diff[f].source_file)

        for f in files_with_removed_lines:
            repo_f = self.get_repo_path_from_registry_path(f)
            if (
                # file may not be in the common starter point at all
                repo_f not in starter_point_file_list
                or (
                    # ignore files with only phantom line changes
                    f in self.phantom_lines.keys()
                    and repo_f not in repository_diff.diff.keys()
                )
            ):
                continue

            c2c = git_blame_delete(
                repository_diff.repo_path,
                repo_f,
                repository_diff.common_starter_commit,
                repository_diff.new_version_commit,
                repository_diff.diff[repo_f],
            )
            for k in list(c2c.keys()):
                c2c[k] = [process_whitespace(l) for l in c2c[k]]
                c2c[k] = [l for l in c2c[k] if l]

            self.removed_loc_to_commit_map[f] = c2c

    def get_stats(self):
        reviewed_lines = non_reviewed_lines = 0
        non_reviewed_commits = set()
        reviewed_commits = set()

        for f in self.added_loc_to_commit_map.keys():
            for commit in self.added_loc_to_commit_map[f].keys():
                cur = len(self.added_loc_to_commit_map[f][commit])
                if self.commit_review_info[commit].review_category:
                    reviewed_lines += cur
                    reviewed_commits.add(commit)
                else:
                    non_reviewed_lines += cur
                    non_reviewed_commits.add(commit)

        for f in self.removed_loc_to_commit_map.keys():
            for commit in self.removed_loc_to_commit_map[f].keys():
                cur = len(self.removed_loc_to_commit_map[f][commit])
                if self.commit_review_info[commit].review_category:
                    reviewed_lines += cur
                    reviewed_commits.add(commit)
                else:
                    non_reviewed_lines += cur
                    non_reviewed_commits.add(commit)

        phantom_files = len(self.phantom_files)

        files_with_phantom_lines = set()
        phantom_lines = 0
        for f in self.phantom_lines.keys():
            for l in self.phantom_lines[f].keys():
                if self.phantom_lines[f][l].additions > 0:
                    files_with_phantom_lines.add(f)
                    phantom_lines += self.phantom_lines[f][l].additions
        files_with_phantom_lines = len(files_with_phantom_lines)

        return DepdiveStats(
            reviewed_lines,
            non_reviewed_lines,
            reviewed_commits,
            non_reviewed_commits,
            phantom_files,
            files_with_phantom_lines,
            phantom_lines,
        )
