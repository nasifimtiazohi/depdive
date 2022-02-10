from package_locator.common import CARGO, PYPI
from version_differ.common import PIP
from version_differ.version_differ import get_version_diff_stats


class VersionDifferError(Exception):
    pass


def get_registry_version_diff(ecosystem, package, old, new):
    if ecosystem == PYPI:
        ecosystem = PIP

    try:
        version_diff = get_version_diff_stats(ecosystem, package, old, new)
    except:
        raise VersionDifferError

    # preprocess auto-gen files respective to each registry
    if ecosystem == CARGO:
        preprocess_cargo_crate_files(version_diff)

    return version_diff


def preprocess_cargo_crate_files(version_diff):
    # filter out auto-generated files
    auto_gen_files = [".cargo_vcs_info.json", "Cargo.lock"]
    for f in auto_gen_files:
        version_diff.diff.pop(f, None)
        version_diff.new_version_filelist.discard(f)
