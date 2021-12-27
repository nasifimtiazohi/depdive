from package_locator.common import CARGO, NPM
from depdive.code_review import CodeReviewAnalysis


def test_code_review_guppy():
    ca = CodeReviewAnalysis(
        CARGO, "guppy", "0.8.0", "0.9.0", "https://github.com/facebookincubator/cargo-guppy", "./guppy"
    )
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_tokio_a():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.8.4",
        "1.9.0",
    )
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_nix():
    ca = CodeReviewAnalysis(CARGO, "nix", "0.22.2", "0.23.0", "https://github.com/nix-rust/nix", "./")
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_acorn():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "acorn", "8.5.0", "8.6.0")
    ca.run_phantom_analysis()
    assert len(ca.phantom_files) == 3
    assert not ca.phantom_lines


def test_code_review_lodash():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "lodash", "4.17.20", "4.17.21")
    ca.run_phantom_analysis()
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


def test_code_review_tokio_b():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.9.0",
        "1.8.4",
    )
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_quote():
    """test phantom lines"""
    ca = CodeReviewAnalysis(
        CARGO,
        "quote",
        "1.0.9",
        "1.0.10",
    )
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_rand():
    ca = CodeReviewAnalysis(
        CARGO,
        "rand",
        "0.8.3",
        "0.8.4",
    )
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_tokio_c():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.13.1",
        "1.14.0",
    )
    ca.run_phantom_analysis()
    assert ca.end_commit == "623c09c52c2c38a8d75e94c166593547e8477707"
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_chalk():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "chalk", "4.1.2", "5.0.0")
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_safe_buffer():
    ca = CodeReviewAnalysis(NPM, "safe-buffer", "5.2.0", "5.2.1")
    ca.run_phantom_analysis()
    assert ca.start_commit == "ae53d5b9f06eae8540ca948d14e43ca32692dd8c"
    assert ca.end_commit == "89d3d5b4abd6308c6008499520373d204ada694b"
    assert not ca.phantom_files
    assert not ca.phantom_lines


def test_code_review_source_map():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "source-map", "0.7.3", "0.8.0-beta.0")
    ca.run_phantom_analysis()
    assert not ca.phantom_files
    assert not ca.phantom_lines
