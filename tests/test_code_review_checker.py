from depdive.code_review_checker import CodeCommitInfo, CodeReviewCategory


def test_cr_tokio():
    cr = CodeCommitInfo("tokio-rs/tokio", "5739d6dcf484b4aa6b539ac018d354937ad33359")
    assert cr.review_cateogry == CodeReviewCategory.GitHubReview

    cr = CodeCommitInfo("tokio-rs/tokio", "9bff885f343c7d530f3737aa071925c40d9889c6")
    assert cr.review_cateogry == CodeReviewCategory.GitHubReview


def test_cr_lodash():
    cr = CodeCommitInfo("lodash/lodash", "4c2e40e7a2fc5e40d4962afad0ea286dfb963da7")
    assert cr.review_cateogry == CodeReviewCategory.DifferentMerger


def test_cr_typo3():
    cr = CodeCommitInfo("typo3/typo3", "a3e2d88ce93475b62dabf001650df2141a948f6f")
    assert cr.review_cateogry == CodeReviewCategory.GerritReview
