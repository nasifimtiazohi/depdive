from package_locator.common import CARGO, NPM
from depdive.code_review import CodeReviewAnalysis


def test_code_review_guppy():
    ca = CodeReviewAnalysis(
        CARGO, "guppy", "0.8.0", "0.9.0", "https://github.com/facebookincubator/cargo-guppy", "./guppy"
    )
    r = ca.run_phantom_analysis()
    assert not r.files
    assert not r.lines


def test_code_review_tokio():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.8.4",
        "1.9.0",
    )
    r = ca.run_phantom_analysis()
    assert not r.files
    assert not r.lines


def test_code_review_nix():
    ca = CodeReviewAnalysis(CARGO, "nix", "0.22.2", "0.23.0", "https://github.com/nix-rust/nix", "./")
    r = ca.run_phantom_analysis()
    assert not r.files
    assert not r.lines


def test_code_review_acorn():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "acorn", "8.5.0", "8.6.0")
    r = ca.run_phantom_analysis()
    assert len(r.files) == 3
    assert not r.lines


def test_code_review_lodash():
    """test phantom files"""
    ca = CodeReviewAnalysis(NPM, "lodash", "4.17.20", "4.17.21")
    r = ca.run_phantom_analysis()
    assert len(r.files) == 14
    assert not r.lines


def test_code_review_tokio():
    ca = CodeReviewAnalysis(
        CARGO,
        "tokio",
        "1.8.4",
        "1.9.0",
    )
    r = ca.run_phantom_analysis()
    assert not r.files
    assert not r.lines


def test_code_review_quote():
    """test phantom lines"""
    ca = CodeReviewAnalysis(
        CARGO,
        "quote",
        "1.0.9",
        "1.0.10",
    )
    r = ca.run_phantom_analysis()
    assert not r.files
    assert not r.lines
