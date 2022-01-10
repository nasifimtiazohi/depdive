from git import exc
from github import Github
import os
from enum import Enum

"""
CORNER CASES
"""

BOT = "[bot]"
# TODO: handle bots?
GITHUB = "web-flow"


class GitHubTokenRateLimitExceeded(Exception):
    pass


class CodeReviewCategory(Enum):
    GitHubReview = 1
    DifferentMerger = 2
    DifferentCommitter = 3
    GerritReview = 3
    ProwReview = 4


class NotGitHubRepo(Exception):
    pass


def get_github_repo_full_name(repository):
    s = "github.com/"
    s = repository[repository.find(s) + len(s) :]
    return "/".join(s.split("/")[:2])


class CommitReviewInfo:
    def __init__(self, repository, commit_sha):
        if "github" not in repository:
            raise NotGitHubRepo
        # TODO: check if a mirror from about section

        self.repo_full_name = get_github_repo_full_name(repository)
        self.commit_sha = commit_sha

        # instantiate github api calls
        self.g = Github(os.environ["GITHUB_TOKEN"])
        self.github_repo = self.g.get_repo(self.repo_full_name)
        self.github_commit = self.github_repo.get_commit(self.commit_sha)

        self.review_category = None
        self.github_pull_requests = []

        checkers = [
            self.github_pr,
            self.gerrit_review,
            self.different_committer,
        ]

        try:
            for check in checkers:
                check()
                if self.review_category:
                    break
        except Exception as e:
            if self.g.get_rate_limit().core.remaining == 0:
                raise GitHubTokenRateLimitExceeded
            else:
                raise e

    def github_pr(self):
        for pr in self.github_commit.get_pulls():
            self.github_pull_requests.append(pr)
            if pr.get_reviews().totalCount > 0:
                self.review_category = CodeReviewCategory.GitHubReview
            elif pr.user.login != pr.merged_by.login and pr.merged_by.login != GITHUB:
                self.review_category = CodeReviewCategory.DifferentMerger
            elif any([l.name in ["lgtm", "approved"] for l in pr.get_labels()]):
                self.review_category = CodeReviewCategory.ProwReview

    def different_committer(self):
        if (
            self.github_commit.author
            and self.github_commit.committer
            and self.github_commit.author.login != self.github_commit.committer.login
            and self.github_commit.committer.login != GITHUB
        ):
            self.review_category = CodeReviewCategory.DifferentCommitter

    def gerrit_review(self):
        message = self.github_commit.commit.message
        if "https://review" in message and "\nReviewed-by: " in message:
            self.review_category = CodeReviewCategory.GerritReview
