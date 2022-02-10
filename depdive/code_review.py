from version_differ.version_differ import FileDiff
from package_locator.locator import get_repository_url_and_subdir
from depdive.common import LineDelta, process_whitespace
from depdive.registry_diff import get_registry_version_diff
from depdive.repository_diff import (
    RepositoryDiff,
    SingleCommitFileChangeData,
    get_repository_file_list,
    UncertainSubdir,
    sort_commits_by_commit_date,
)
from depdive.code_review_checker import CommitReviewInfo


class PackageDirectoryChanged(Exception):
    pass


class DepdiveStats:
    def __init__(
        self,
        added_reviewed_lines,
        added_non_reviewed_lines,
        removed_reviewed_lines,
        removed_non_reviewed_lines,
        reviewed_commits,
        non_reviewed_commits,
        phantom_files,
        files_with_phantom_lines,
        phantome_lines,
    ) -> None:
        self.added_reviewed_lines = added_reviewed_lines
        self.added_non_reviewed_lines = added_non_reviewed_lines
        self.removed_reviewed_lines = removed_reviewed_lines
        self.removed_non_reviewed_lines = removed_non_reviewed_lines

        self.reviewed_lines = self.added_reviewed_lines + self.removed_reviewed_lines
        self.non_reviewed_lines = self.added_non_reviewed_lines + self.removed_non_reviewed_lines

        self.total_commit_count = len(reviewed_commits) + len(non_reviewed_commits)
        self.reviewed_commit_count = len(reviewed_commits)

        self.reviewed_commits = reviewed_commits
        self.non_reviewed_commits = non_reviewed_commits

        self.phantom_files = phantom_files
        self.files_with_phantom_lines = files_with_phantom_lines
        self.phantom_lines = phantome_lines

    def print(self):
        print(self.reviewed_commits, self.non_reviewed_commits)
        print(
            self.added_reviewed_lines,
            self.added_non_reviewed_lines,
            self.removed_reviewed_lines,
            self.removed_non_reviewed_lines,
        )
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

    def get_repo_path_from_registry_path(self, filepath, repo_file_list):
        subdir = self.directory.removeprefix("./").removesuffix("/")
        repo_f = subdir + "/" + filepath if subdir else filepath

        if filepath == "LICENSE":
            if repo_f not in repo_file_list and filepath in repo_file_list:
                return filepath

        return repo_f

    def _process_phantom_files(self, registry_diff, repo_file_list):
        """
        Phantom files: Files that are present in the registry,
                        but not in the source repository

        Also, keep track of files that are present in the repository,
        but have been removed in the new version
        """
        for f in registry_diff.new_version_filelist:
            repo_f = self.get_repo_path_from_registry_path(f, repo_file_list)
            if repo_f not in repo_file_list:
                self.phantom_files.add(f)

        for f in registry_diff.diff.keys():
            repo_f = self.get_repo_path_from_registry_path(f, repo_file_list)
            if not registry_diff.diff[f].target_file and repo_f in repo_file_list:
                self.removed_files_in_registry[f] = registry_diff.diff[f]

    def _get_phantom_lines_in_a_file(self, registry_file_diff, repo_file_diff):
        phantom = {}
        for l in registry_file_diff:
            if (
                l not in repo_file_diff.changed_lines
                or registry_file_diff[l].delta() != repo_file_diff.changed_lines[l].delta()
            ):
                phantom[l] = LineDelta(registry_file_diff[l].additions, registry_file_diff[l].deletions)
                if l in repo_file_diff.changed_lines:
                    phantom[l].subtract(repo_file_diff.changed_lines[l])

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
        new_version_repo_filelist = get_repository_file_list(
            repository_diff.repo_path, repository_diff.new_version_commit
        )
        for f in registry_diff.diff.keys():
            registry_file_diff = self._get_registry_file_line_counter(registry_diff.diff[f])
            self.registry_diff[f] = registry_file_diff

            if not registry_diff.diff[f].target_file:
                continue

            repo_f = self.get_repo_path_from_registry_path(f, repository_diff.new_version_file_list)

            if (
                not registry_diff.diff[f].source_file
                and repo_f in new_version_repo_filelist
                and (repo_f not in repository_diff.diff.keys() or not repository_diff.diff[repo_f].is_rename)
            ):
                # possible explanation: newly included file to be published - get all the commits from the beginning
                # get full file history for such files
                repository_diff.get_full_file_history(repo_f, end_commit=repository_diff.new_version_commit)

            phantom_lines = self._get_phantom_lines_in_a_file(
                registry_file_diff, repository_diff.single_diff.get(repo_f, SingleCommitFileChangeData())
            )
            if phantom_lines:
                # try looking beyond the initial commit boundary
                has_commit_boundary_changed = repository_diff.traverse_beyond_new_version_commit(
                    repo_f,
                    phantom_lines.copy(),
                )

                if has_commit_boundary_changed:
                    return False

            if phantom_lines:
                self.phantom_lines[f] = phantom_lines
        return True

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

        phantom_lines_processed = False
        while not phantom_lines_processed:
            phantom_lines_processed = self._proccess_phantom_lines(registry_diff, repository_diff)

        self.start_commit = repository_diff.old_version_commit
        self.end_commit = repository_diff.new_version_commit

        self.map_commit_to_added_lines(repository_diff, registry_diff)
        self.map_commit_to_removed_lines(repository_diff, registry_diff)

        for f in registry_diff.diff.keys():
            repo_files = [self.get_repo_path_from_registry_path(f, repository_diff.new_version_file_list)]
            if registry_diff.diff[f].is_rename:
                repo_files += [
                    self.get_repo_path_from_registry_path(
                        registry_diff.diff[f].source_file, repository_diff.new_version_file_list
                    )
                ]
            for repo_f in repo_files:
                if repo_f in repository_diff.diff.keys():
                    for commit in repository_diff.diff[repo_f].commits:
                        if commit not in self.commit_review_info:
                            self.commit_review_info[commit] = CommitReviewInfo(self.repository, commit)

        self.stats = self.get_stats()
        repository_diff.cleanup()

    def map_commit_to_added_lines(self, repository_diff, registry_diff):
        def map_submdule_to_added_lines(f, repo_f):
            for path in repository_diff.submodule_paths:
                if "{}/".format(path) in repo_f:
                    commits = sort_commits_by_commit_date(
                        repository_diff.repo_path, list(repository_diff.diff[repo_f].commits)
                    )
                    assert commits, "no commit found for submodule {}".format(path)
                    commit = commits[-1]

                    added_lines = [process_whitespace(l) for l in registry_diff.diff[f].added_lines]
                    added_lines = [l for l in added_lines if l]
                    self.added_loc_to_commit_map[f] = {commit: added_lines}
                    return True
            return False

        files_with_added_lines = set()
        for f in registry_diff.diff.keys():
            if registry_diff.diff[f].target_file and registry_diff.diff[f].added_lines:
                files_with_added_lines.add(registry_diff.diff[f].target_file)

        for f in files_with_added_lines:
            repo_f = self.get_repo_path_from_registry_path(f, repository_diff.new_version_file_list)

            # ignore files with only phantom line changes
            if f in self.phantom_lines.keys() and repo_f not in repository_diff.diff.keys():
                continue

            # check if file is in a submodule
            if map_submdule_to_added_lines(f, repo_f):
                continue

            c2c = repository_diff.git_blame(repo_f, repository_diff.new_version_commit)

            for commit in list(c2c.keys()):
                if commit not in repository_diff.diff[repo_f].commits:
                    c2c.pop(commit)
                else:
                    c2c[commit] = [process_whitespace(l) for l in c2c[commit]]
                    c2c[commit] = [l for l in c2c[commit] if l]

            self.added_loc_to_commit_map[f] = c2c

    def map_commit_to_removed_lines(self, repository_diff, registry_diff):
        def map_submdule_to_removed_lines(f, repo_f):
            for path in repository_diff.submodule_paths:
                if "{}/".format(path) in repo_f:
                    commits = sort_commits_by_commit_date(
                        repository_diff.repo_path, list(repository_diff.diff[repo_f].commits)
                    )
                    assert commits, "no commit found for submodule {}".format(path)
                    commit = commits[0]

                    removed_lines = [process_whitespace(l) for l in registry_diff.diff[f].removed_lines]
                    removed_lines = [l for l in removed_lines if l]
                    self.removed_loc_to_commit_map[f] = {commit: removed_lines}
                    return True
            return False

        starter_point_file_list = get_repository_file_list(
            repository_diff.repo_path, repository_diff.common_ancestor_commit_new_and_old_version
        )

        files_with_removed_lines = set()
        for f in registry_diff.diff.keys():
            if registry_diff.diff[f].source_file and registry_diff.diff[f].removed_lines:
                files_with_removed_lines.add(registry_diff.diff[f].source_file)

        for f in files_with_removed_lines:
            repo_f = self.get_repo_path_from_registry_path(f, repository_diff.new_version_file_list)

            # file may not be in version diff in repo
            # possible explanations:
            # 1. file may not be in the common starter point at all
            # 2. phantom line changes
            if repo_f not in starter_point_file_list or repo_f not in repository_diff.diff.keys():
                continue

            if map_submdule_to_removed_lines(f, repo_f):
                continue

            c2c = repository_diff.git_blame_delete(
                repo_f, repository_diff.common_ancestor_commit_new_and_old_version, repository_diff.new_version_commit
            )
            for commit in list(c2c.keys()):
                if commit not in repository_diff.commits:
                    c2c.pop(commit)
                else:
                    c2c[commit] = [process_whitespace(l) for l in c2c[commit]]
                    c2c[commit] = [l for l in c2c[commit] if l]

            self.removed_loc_to_commit_map[f] = c2c

    def get_stats(self):
        added_reviewed_lines = added_non_reviewed_lines = 0
        non_reviewed_commits = set()
        reviewed_commits = set()

        for f in self.added_loc_to_commit_map.keys():
            for commit in self.added_loc_to_commit_map[f].keys():
                cur = len(self.added_loc_to_commit_map[f][commit])
                if self.commit_review_info[commit].review_category:
                    added_reviewed_lines += cur
                    reviewed_commits.add(commit)
                else:
                    added_non_reviewed_lines += cur
                    non_reviewed_commits.add(commit)

        removed_reviewed_lines = removed_non_reviewed_lines = 0
        for f in self.removed_loc_to_commit_map.keys():
            for commit in self.removed_loc_to_commit_map[f].keys():
                cur = len(self.removed_loc_to_commit_map[f][commit])
                if self.commit_review_info[commit].review_category:
                    removed_reviewed_lines += cur
                    reviewed_commits.add(commit)
                else:
                    removed_non_reviewed_lines += cur
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
            added_reviewed_lines,
            added_non_reviewed_lines,
            removed_reviewed_lines,
            removed_non_reviewed_lines,
            reviewed_commits,
            non_reviewed_commits,
            phantom_files,
            files_with_phantom_lines,
            phantom_lines,
        )
