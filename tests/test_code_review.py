from package_locator.common import CARGO, NPM
from depdive.code_review import CodeReviewAnalysis
import pytest
from depdive.registry_diff import VersionDifferError
from depdive.repository_diff import ReleaseCommitNotFound


def test_code_review_guppy():
    ca = CodeReviewAnalysis(
        CARGO, "guppy", "0.8.0", "0.9.0", "https://github.com/facebookincubator/cargo-guppy", "./guppy"
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl


def test_code_review_tokio_a():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.8.4",
        "1.9.0",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_nix():
    ca = CodeReviewAnalysis(CARGO, "nix", "0.22.2", "0.23.0", "https://github.com/nix-rust/nix", "./")
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_acorn():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "acorn", "8.5.0", "8.6.0")
    ca.map_code_to_commit()
    assert len(ca.phantom_files) == 3
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl


def test_code_review_lodash():
    """test phantom files and lines"""
    ca = CodeReviewAnalysis(NPM, "lodash", "4.17.20", "4.17.21")
    ca.map_code_to_commit()
    assert len(ca.phantom_files) == 14
    assert len(ca.phantom_lines) == 1
    assert len(ca.phantom_lines["README.md"]) == 2
    assert (
        "See the [package source](https://github.com/lodash/lodash/tree/4.17.21-npm) for more details."
        in ca.phantom_lines["README.md"]
    )
    assert (
        "See the [package source](https://github.com/lodash/lodash/tree/4.17.20-npm) for more details."
        in ca.phantom_lines["README.md"]
    )

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    # README.md and package.json oare different in registry and repo

    assert cl - 4 == al - 1

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl - 4 == rl - 1


def test_code_review_tokio_b():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.9.0",
        "1.8.4",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_quote():
    ca = CodeReviewAnalysis(
        CARGO,
        "quote",
        "1.0.9",
        "1.0.10",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl


def test_code_review_syn():
    ca = CodeReviewAnalysis(
        CARGO,
        "syn",
        "1.0.83",
        "1.0.84",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl


def test_code_review_minimist():
    ca = CodeReviewAnalysis(
        NPM,
        "minimist",
        "1.2.3",
        "1.2.5",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl


def test_code_review_rand():
    ca = CodeReviewAnalysis(
        CARGO,
        "rand",
        "0.8.3",
        "0.8.4",
    )
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_tokio_c():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.13.1",
        "1.14.0",
    )
    ca.map_code_to_commit()
    assert ca.end_commit == "623c09c52c2c38a8d75e94c166593547e8477707"
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_chalk():
    ca = CodeReviewAnalysis(NPM, "chalk", "4.1.2", "5.0.0")
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_safe_buffer():
    ca = CodeReviewAnalysis(NPM, "safe-buffer", "5.2.0", "5.2.1")
    ca.map_code_to_commit()
    assert ca.start_commit == "ae53d5b9f06eae8540ca948d14e43ca32692dd8c"
    assert ca.end_commit == "89d3d5b4abd6308c6008499520373d204ada694b"
    assert not ca.phantom_files
    assert not ca.phantom_lines

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    # for f in ca.registry_diff.keys():
    #     rg = 0
    #     if f not in ca.phantom_files:
    #         for l in ca.registry_diff[f].keys():
    #             rg += ca.registry_diff[f][l].additions
    #     rp = 0
    #     for c in ca.c2c_added_lines[f].keys():
    #         rp += len(ca.c2c_added_lines[f][c])
    #     if rg != rp:
    #         print(f)
    #         print(ca.c2c_added_lines)
    #         for l in ca.registry_diff[f].keys():
    #             print(l)
    #             print(ca.registry_diff[f][l].additions)
    #             print(ca.registry_diff[f][l].deletions)

    assert cl - 1 == al

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl - 1 == rl


def test_code_review_source_map():
    ca = CodeReviewAnalysis(NPM, "source-map", "0.7.3", "0.8.0-beta.0")
    ca.map_code_to_commit()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_uuid():
    with pytest.raises(ReleaseCommitNotFound):
        ca = CodeReviewAnalysis(NPM, "uuid", "8.3.2-beta.0", "8.3.2")
        ca.map_code_to_commit()


def test_code_review_babel():
    ca = CodeReviewAnalysis(NPM, "@babel/highlight", "7.14.5", "7.16.0")
    ca.map_code_to_commit()
    assert len(ca.phantom_files) == 1
    assert len(ca.phantom_lines) == 1


def test_code_review_rayon():
    with pytest.raises(ReleaseCommitNotFound):
        ca = CodeReviewAnalysis(CARGO, "rayon", "1.5.0", "1.5.1")
        ca.map_code_to_commit()


def test_code_review_num_bigint():
    with pytest.raises(VersionDifferError):
        ca = CodeReviewAnalysis(CARGO, "num-bigint", "0.4.2", "0.4.3")
        ca.map_code_to_commit()
