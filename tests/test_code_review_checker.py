from depdive.code_review_checker import CommitReviewInfo, CodeReviewCategory


def test_cr_tokio():
    cr = CommitReviewInfo("https://github.com/tokio-rs/tokio/", "5739d6dcf484b4aa6b539ac018d354937ad33359")
    assert cr.review_category == CodeReviewCategory.GitHubReview

    cr = CommitReviewInfo("https://github.com/tokio-rs/tokio/", "9bff885f343c7d530f3737aa071925c40d9889c6")
    assert cr.review_category == CodeReviewCategory.GitHubReview


def test_cr_lodash():
    cr = CommitReviewInfo("https://github.com/lodash/lodash", "4c2e40e7a2fc5e40d4962afad0ea286dfb963da7")
    assert cr.review_category == CodeReviewCategory.DifferentMerger

    cr = CommitReviewInfo("https://github.com/lodash/lodash", "3469357cff396a26c363f8c1b5a91dde28ba4b1c")
    assert cr.review_category == CodeReviewCategory.DifferentCommitter


def test_cr_typo3():
    cr = CommitReviewInfo("https://github.com/TYPO3/typo3", "a3e2d88ce93475b62dabf001650df2141a948f6f")
    assert cr.review_category == CodeReviewCategory.GerritReview


def test_cr_acorn():
    cr = CommitReviewInfo("https://github.com/acornjs/acorn", "9cff83e2d1b22c251e57f2117297029466584b92")
    assert cr.review_category == CodeReviewCategory.DifferentMerger


def test_cr_syn():
    cr = CommitReviewInfo("https://github.com/dtolnay/syn", "002a247c192aa5fc841d731a93df02a675127b0e")
    assert cr.review_category is None


def test_cr_pry():
    cr = CommitReviewInfo("https://github.com/pry/pry/", "033f69b3afcce57ed8d8b68f297457d1a80b1e6c")
    assert cr.review_category == CodeReviewCategory.DifferentMerger
