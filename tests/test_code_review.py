from package_locator.common import CARGO, NPM, PYPI, RUBYGEMS
from depdive.code_review import CodeReviewAnalysis, UncertainSubdir
import pytest
from depdive.code_review_checker import GitHubAPIUnknownObject
from depdive.registry_diff import VersionDifferError
from depdive.repository_diff import GitError, ReleaseCommitNotFound


def test_code_review_guppy():
    ca = CodeReviewAnalysis(
        CARGO, "guppy", "0.8.0", "0.9.0", "https://github.com/facebookincubator/cargo-guppy", "./guppy"
    )
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

    stats = ca.stats
    assert stats.reviewed_lines == 11
    assert stats.non_reviewed_lines == 246
    assert stats.total_commit_count == 14
    assert stats.reviewed_commit_count == 8


def test_code_review_tokio_a():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.8.4",
        "1.9.0",
    )
    assert not ca.phantom_files
    assert not ca.phantom_lines

    # versions come from different branches, therefore,
    # can't compare mapped loc to registry diff

    stats = ca.stats
    assert stats.non_reviewed_lines == 0


def test_code_review_nix():
    ca = CodeReviewAnalysis(CARGO, "nix", "0.22.2", "0.23.0", "https://github.com/nix-rust/nix", "./")
    assert not ca.phantom_files
    assert not ca.phantom_lines

    # versions come from different branches, therefore,
    # can't compare mapped loc to registry diff

    stats = ca.stats
    stats.print()
    assert stats.reviewed_lines == 5677
    assert stats.non_reviewed_lines == 395
    assert stats.total_commit_count == 154
    assert stats.reviewed_commit_count == 120
    assert len(ca.removed_files_in_registry) == 43


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_acorn():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "acorn", "8.5.0", "8.6.0")
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

    stats = ca.stats
    stats.non_reviewed_lines == 7


def test_code_review_lodash():
    """test phantom files and lines"""
    ca = CodeReviewAnalysis(NPM, "lodash", "4.17.20", "4.17.21")
    assert len(ca.phantom_files) == 1046
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

    stats = ca.stats
    assert stats.phantom_files == 1046
    assert stats.files_with_phantom_lines == 1
    assert stats.phantom_lines == 1
    assert stats.reviewed_lines == 58
    assert stats.non_reviewed_lines == 14
    assert stats.total_commit_count == 3
    assert stats.reviewed_commit_count == 2


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_tokio_b():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.9.0",
        "1.8.4",
    )
    assert not ca.phantom_files
    assert not ca.phantom_lines

    # versions come from different branches, therefore,
    # can't compare mapped loc to registry diff

    stats = ca.stats
    stats.non_reviewed_lines == 0


def test_code_review_quote():
    ca = CodeReviewAnalysis(
        CARGO,
        "quote",
        "1.0.9",
        "1.0.10",
    )
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

    stats = ca.stats
    assert stats.reviewed_lines == 20
    assert stats.non_reviewed_lines == 395
    assert stats.total_commit_count == 29
    assert stats.reviewed_commit_count == 2


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_syn():
    ca = CodeReviewAnalysis(
        CARGO,
        "syn",
        "1.0.83",
        "1.0.84",
    )
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

    stats = ca.stats
    stats.reviewed_lines == 0


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_minimist():
    ca = CodeReviewAnalysis(
        NPM,
        "minimist",
        "1.2.3",
        "1.2.5",
    )
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

    stats = ca.stats
    stats.non_reviewed_lines == 0


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_rand():
    ca = CodeReviewAnalysis(
        CARGO,
        "rand",
        "0.8.3",
        "0.8.4",
    )
    assert not ca.phantom_files
    assert not ca.phantom_lines

    stats = ca.stats
    assert stats.reviewed_lines == 787
    assert stats.non_reviewed_lines == 0
    assert stats.total_commit_count == 36
    assert stats.reviewed_commit_count == 36


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_tokio_c():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.13.1",
        "1.14.0",
    )
    assert ca.end_commit == "623c09c52c2c38a8d75e94c166593547e8477707"
    assert not ca.phantom_files
    assert not ca.phantom_lines

    stats = ca.stats
    assert stats.reviewed_lines == 448
    assert stats.non_reviewed_lines == 0
    assert stats.total_commit_count == 12
    assert stats.reviewed_commit_count == 12


def test_code_review_chalk():
    ca = CodeReviewAnalysis(NPM, "chalk", "4.1.2", "5.0.0")
    assert not ca.phantom_files
    assert not ca.phantom_lines

    # file renamed makes cl and al,rl different

    stats = ca.stats
    assert stats.reviewed_lines == 375
    assert stats.non_reviewed_lines == 1075
    assert stats.total_commit_count == 26
    assert stats.reviewed_commit_count == 11


def test_code_review_safe_buffer():
    ca = CodeReviewAnalysis(NPM, "safe-buffer", "5.2.0", "5.2.1")
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

    stats = ca.stats
    assert stats.non_reviewed_lines == 24


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_source_map():
    ca = CodeReviewAnalysis(NPM, "source-map", "0.7.3", "0.8.0-beta.0")
    assert not ca.phantom_files
    assert not ca.phantom_lines 

    cal = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cal += len(ca.added_loc_to_commit_map[f][c])
    assert cal == 475


    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions
    
    assert al == 482
                


    crl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            crl += len(ca.removed_loc_to_commit_map[f][c])

    assert crl == 3693

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions
    
    assert rl == 3699

    stats = ca.stats
    assert stats.reviewed_lines == 3441
    assert stats.non_reviewed_lines == 727
    assert stats.total_commit_count == 11
    assert stats.reviewed_commit_count == 6


def test_code_review_uuid():
    with pytest.raises(ReleaseCommitNotFound):
        ca = CodeReviewAnalysis(NPM, "uuid", "8.3.2-beta.0", "8.3.2")


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_babel():
    ca = CodeReviewAnalysis(NPM, "@babel/highlight", "7.14.5", "7.16.0")
    assert len(ca.phantom_files) == 2
    assert len(ca.phantom_lines) == 1
    ca.stats.print()

    stats = ca.stats
    assert stats.phantom_lines == 1
    assert stats.reviewed_lines == 2
    assert stats.non_reviewed_lines == 2
    assert stats.total_commit_count == 2
    assert stats.reviewed_commit_count == 1


def test_code_review_num_bigint():
    with pytest.raises(VersionDifferError):
        ca = CodeReviewAnalysis(CARGO, "num-bigint", "0.4.2", "0.4.3")


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_requests():
    ca = CodeReviewAnalysis(PYPI, "requests", "2.27.0", "2.27.1")
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

    assert ca.stats.non_reviewed_lines == 0


def test_code_review_pytest():
    ca = CodeReviewAnalysis(PYPI, "pytest", "6.2.0", "6.2.5")
    print(ca.phantom_files)
    stats = ca.stats
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

    assert stats.phantom_files == 1
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 58
    assert stats.non_reviewed_lines == 80
    assert stats.total_commit_count == 10
    assert stats.reviewed_commit_count == 3


def test_code_review_numpy():
    ca = CodeReviewAnalysis(PYPI, "numpy", "1.21.4", "1.21.5")
    stats = ca.stats

    cl = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cl += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    assert cl == al - 3

    cl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            cl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cl == rl - 3

    assert stats.phantom_files == 39
    assert stats.files_with_phantom_lines == 1
    assert stats.phantom_lines == 3
    assert stats.reviewed_lines == 245
    assert stats.non_reviewed_lines == 12
    assert stats.total_commit_count == 10
    assert stats.reviewed_commit_count == 9


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_pry():
    ca = CodeReviewAnalysis(RUBYGEMS, "pry", "0.14.0", "0.14.1")
    stats = ca.stats

    # versions come from different branches, therefore,
    # can't compare mapped loc to registry diff

    assert stats.phantom_files == 0
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 42
    assert stats.non_reviewed_lines == 29
    assert stats.total_commit_count == 11
    assert stats.reviewed_commit_count == 6


def test_code_review_pundit():
    ca = CodeReviewAnalysis(RUBYGEMS, "pundit", "2.1.0", "2.1.1")
    stats = ca.stats

    cal = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cal += len(ca.added_loc_to_commit_map[f][c])

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    crl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            crl += len(ca.removed_loc_to_commit_map[f][c])

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cal - crl == al - rl

    assert stats.phantom_files == 0
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 128
    assert stats.non_reviewed_lines == 186
    assert stats.total_commit_count == 35
    assert stats.reviewed_commit_count == 23


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_nltk():
    ca = CodeReviewAnalysis(PYPI, "nltk", "3.6.5", "3.6.7")
    stats = ca.stats

    assert stats.phantom_files == 0
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 6622
    assert stats.non_reviewed_lines == 25
    assert stats.total_commit_count == 43
    assert stats.reviewed_commit_count == 33


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_pyyaml():
    with pytest.raises(UncertainSubdir):
        ca = CodeReviewAnalysis(PYPI, "pyyaml", "5.4.1", "6.0")


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_excon():
    ca = CodeReviewAnalysis(RUBYGEMS, "excon", "0.9.5", "0.9.6")
    stats = ca.stats

    cal = 0
    for f in ca.added_loc_to_commit_map.keys():
        for c in ca.added_loc_to_commit_map[f].keys():
            cal += len(ca.added_loc_to_commit_map[f][c])
            for l in ca.added_loc_to_commit_map[f][c]:
                if l not in ca.registry_diff[f]:
                    print(f, c, l)

    al = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                al += ca.registry_diff[f][l].additions

    crl = 0
    for f in ca.removed_loc_to_commit_map.keys():
        for c in ca.removed_loc_to_commit_map[f].keys():
            crl += len(ca.removed_loc_to_commit_map[f][c])
            for l in ca.removed_loc_to_commit_map[f][c]:
                if l not in ca.registry_diff[f]:
                    print(f, c, l)

    rl = 0
    for f in ca.registry_diff.keys():
        if f not in ca.phantom_files:
            for l in ca.registry_diff[f].keys():
                rl += ca.registry_diff[f][l].deletions

    assert cal - crl - 1 == al - rl

    assert stats.phantom_files == 0
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 27
    assert stats.non_reviewed_lines == 143
    assert stats.total_commit_count == 12
    assert stats.reviewed_commit_count == 5


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_deepmerge():
    ca = CodeReviewAnalysis(NPM, "deepmerge", "4.2.1", "4.2.2")
    stats = ca.stats
    assert stats.phantom_files == 2
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 0
    assert stats.non_reviewed_lines == 39
    assert stats.total_commit_count == 4
    assert stats.reviewed_commit_count == 0


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_xmlbuilder():
    ca = CodeReviewAnalysis(NPM, "xmlbuilder", "15.1.0", "15.1.1")
    ca.stats.print()


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_tokio_d():
    ca = CodeReviewAnalysis(CARGO, "tokio", "1.14.0", "1.15.0")
    assert not ca.phantom_lines


def test_code_review_registry():
    ca = CodeReviewAnalysis(CARGO, "signal-hook-registry", "1.3.0", "1.4.0")
    stats = ca.stats
    assert stats.phantom_files == 0
    # phantom line was actually in the old version
    assert stats.files_with_phantom_lines == 1
    assert stats.phantom_lines == 1
    assert stats.reviewed_lines == 5
    assert stats.non_reviewed_lines == 3
    assert stats.total_commit_count == 4
    assert stats.reviewed_commit_count == 2


@pytest.mark.skip(reason="to limit API calls")
def test_code_review_which():
    ca = CodeReviewAnalysis(CARGO, "which", "4.2.1", "4.2.2")
    stats = ca.stats
    assert stats.phantom_files == 0
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 2
    assert stats.non_reviewed_lines == 2
    assert stats.total_commit_count == 2
    assert stats.reviewed_commit_count == 1


def test_code_review_chrome():
    with pytest.raises(GitHubAPIUnknownObject):
        ca = CodeReviewAnalysis(NPM, "chrome-trace-event", "1.0.2", "1.0.3")


def test_code_review_signature():
    with pytest.raises(GitError):
        ca = CodeReviewAnalysis(CARGO, "signature", "1.3.2", "1.4.0")


def test_code_review_mlflow():
    ca = CodeReviewAnalysis(PYPI, "mlflow", "1.21.0", "1.22.0")
    stats = ca.stats
    stats.print()

    assert stats.phantom_files == 66
    assert stats.files_with_phantom_lines == 0
    assert stats.phantom_lines == 0
    assert stats.reviewed_lines == 676078
    assert stats.non_reviewed_lines == 2
    assert stats.total_commit_count == 43
    assert stats.reviewed_commit_count == 42
