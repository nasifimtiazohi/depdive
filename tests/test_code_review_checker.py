from depdive.code_review_checker import CommitReviewInfo, CodeReviewCategory
import os
import json
import pytest


def test_cr_tokio():
    cr = CommitReviewInfo("https://github.com/tokio-rs/tokio/", "5739d6dcf484b4aa6b539ac018d354937ad33359")
    assert cr.review_category == CodeReviewCategory.GitHubReview
    assert cr.review_metadata.creator.login == "elichai"
    assert len(list(cr.review_metadata.reviewers)) == 3

    cr = CommitReviewInfo("https://github.com/tokio-rs/tokio/", "9bff885f343c7d530f3737aa071925c40d9889c6")
    assert cr.review_category == CodeReviewCategory.GitHubReview


def test_cr_lodash():
    cr = CommitReviewInfo("https://github.com/lodash/lodash", "4c2e40e7a2fc5e40d4962afad0ea286dfb963da7")
    assert cr.review_category == CodeReviewCategory.DifferentMerger
    cr.review_metadata.author.id == 40483898
    cr.review_metadata.author.login == "jacob-lcs"
    cr.review_metadata.merger.id == 4303
    cr.review_metadata.merger.login == "jdalton"

    cr = CommitReviewInfo("https://github.com/lodash/lodash", "3469357cff396a26c363f8c1b5a91dde28ba4b1c")
    assert cr.review_category == CodeReviewCategory.DifferentCommitter
    assert cr.review_metadata.author.id == 439401
    assert cr.review_metadata.author.login == "stof"
    assert cr.review_metadata.committer.id == 813865
    cr.review_metadata.committer.login == "bnjmnt4n"


def test_cr_typo3():
    cr = CommitReviewInfo("https://github.com/TYPO3/typo3", "a3e2d88ce93475b62dabf001650df2141a948f6f")
    assert cr.review_category == CodeReviewCategory.GerritReview
    assert "Reviewed-by:" in cr.review_metadata.message


def test_cr_acorn():
    cr = CommitReviewInfo("https://github.com/acornjs/acorn", "9cff83e2d1b22c251e57f2117297029466584b92")
    assert cr.review_category == CodeReviewCategory.DifferentMerger


def test_cr_syn():
    cr = CommitReviewInfo("https://github.com/dtolnay/syn", "002a247c192aa5fc841d731a93df02a675127b0e")
    assert cr.review_category is None


def test_cr_pry_multiple_token():
    with open("env/tokens.json", "r") as f:
        tokens = json.load(f)
    os.environ["GITHUB_TOKEN"] = json.dumps(tokens)

    cr = CommitReviewInfo("https://github.com/pry/pry/", "033f69b3afcce57ed8d8b68f297457d1a80b1e6c")
    assert cr.review_category == CodeReviewCategory.DifferentMerger

    cr = CommitReviewInfo("https://github.com/pry/pry/", "60e84ee1d80919b0cc41268a878ffc9e78f903ac")
    assert cr.review_category == CodeReviewCategory.DifferentMerger


@pytest.mark.skip(reason="botocore is a tricky repo")
def test_cr_botocore():
    cr = CommitReviewInfo("https://github.com/boto/botocore", "e356b9fff45125be2b0d72e3c6d770344d8dd6a6")
    print(cr.review_category.value)
