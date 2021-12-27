from package_locator.common import CARGO
from version_differ.version_differ import get_version_diff_stats


def get_registry_version_diff(ecosystem, package, old, new):
    version_diff = get_version_diff_stats(ecosystem, package, old, new)

    # preprocess auto-gen files respective to each registry
    if ecosystem == CARGO:
        preprocess_cargo_crate_files(version_diff.diff)

    return version_diff


def preprocess_cargo_crate_files(files):
    # handle Cargo's handling of Cargo.toml file
    if "Cargo.toml.orig" in files:
        files.pop("Cargo.toml", None)
        files["Cargo.toml"] = files["Cargo.toml.orig"]
        files.pop("Cargo.toml.orig", None)

    # filter out auto-generated files
    auto_gen_files = [".cargo_vcs_info.json", "Cargo.lock"]
    for f in auto_gen_files:
        files.pop(f, None)
