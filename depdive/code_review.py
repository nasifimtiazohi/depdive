from re import sub
from git import repo
from package_locator.locator import get_repository_url_and_subdir
from package_locator.common import CARGO, NPM, PYPI, COMPOSER, RUBYGEMS
from depdive.registry_diff import get_registry_version_diff
from depdive.repository_diff import AddDelData, get_repository_diff


class PhantomReport:
    def __init__(self, files, lines):
        self.files = files  # files present in registry but not in present
        self.lines = lines  # files present in repo but contains lines
        # that are only present in registry


class CodeReviewAnalysis:
    def __init__(self, ecosystem, package, old_version, new_version, repository=None, directory=None):
        self.ecosystem = ecosystem
        self.package = package
        self.old_version = old_version
        self.new_version = new_version

        self.repository = repository
        self.directory = directory
        if not self.repository:
            self._locate_repository()
        self.directory = self.directory.removeprefix("./")

    def _locate_repository(self):
        self.repository, self.directory = get_repository_url_and_subdir(self.ecosystem, self.package)

    def get_repo_path_from_registry_path(self, filepath):
        return self.directory + "/" + filepath if self.directory else filepath

    def _get_phantom_files(self, registry_diff, repository_diff):
        """
        Phantom files: Files that are present in the registry,
                        but not in the source repository
        """
        phantom_files = {}
        for f in registry_diff.keys():
            if self.get_repo_path_from_registry_path(f) not in repository_diff.keys():
                # TODO: newly added files in registry
                # TODO: do we need to handle file renaming?
                phantom_files[f] = registry_diff[f]
        return phantom_files

    def _get_phantom_lines_in_a_file(self, registry_file_diff, repo_file_diff):
        d = {}  # total addition and deletion in repo_file
        for l in repo_file_diff.keys():
            d[l] = d.get(l, AddDelData())
            for commit in repo_file_diff[l].keys():
                d[l].add(repo_file_diff[l][commit])

        phantom = {}
        for l in registry_file_diff.added_lines:
            if l in d and d[l].additions > 0:
                d[l].additions -= 1
            else:
                phantom[l] = phantom.get(l, AddDelData(0, 0))
                phantom[l].additions += 1

        for l in registry_file_diff.removed_lines:
            if l in d and d[l].deletions > 0:
                d[l].deletions -= 1
            else:
                phantom[l] = phantom.get(l, AddDelData(0, 0))
                phantom[l].deletions += 1
        return phantom

    def run_phantom_analysis(self):
        """
        Phantom: present in the registry, but not in the source repository
        """
        if not self.repository:
            self._locate_repository()

        registry_diff_data = get_registry_version_diff(self.ecosystem, self.package, self.old_version, self.new_version)
        repository_diff_data = get_repository_diff(self.package, self.repository, self.old_version, self.new_version)

        registry_diff = registry_diff_data.diff
        repository_diff = repository_diff_data.diff

        phantom_files = self._get_phantom_files(registry_diff, repository_diff)
        phantom_file_lines = {}
        for pf in phantom_files.keys():
            registry_diff.pop(pf, None)

        for pf in list(phantom_files.keys()):
            if self.get_repo_path_from_registry_path(pf) in repository_diff_data.new_version_file_list:
                phantom_lines = self._get_phantom_lines_in_a_file(phantom_files[pf], {})  # not in repo diff
                if phantom_lines:
                    phantom_file_lines[pf] = phantom_lines
                phantom_files.pop(pf)

        for k in registry_diff.keys():
            phantom_lines = self._get_phantom_lines_in_a_file(
                registry_diff[k], repository_diff[self.get_repo_path_from_registry_path(k)]
            )
            if phantom_lines:
                phantom_file_lines[k] = phantom_lines

        return PhantomReport(phantom_files, phantom_file_lines)


# cra = CodeReviewAnalysis(CARGO, "nix", "0.22.2", "0.23.0",
#     "https://github.com/nix-rust/nix", "./",)

# f = cra.run_phantom_analysis()


# print(f)
