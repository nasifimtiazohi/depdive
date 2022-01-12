from git import exc
from github import Github
import os
from enum import Enum
import json

import github
from github.GithubException import GithubException

"""
CORNER CASES
"""

BOT = "[bot]"
# TODO: handle bots?
GITHUB = "web-flow"


class AllGitHubTokensRateLimitExceeded(Exception):
    pass


class GitHubAPIUnknownObject(Exception):
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
        self.g = self._get_github_caller()
        while True:
            self.github_repo = self.g.get_repo(self.repo_full_name)
            try:
                self.github_commit = self.github_repo.get_commit(self.commit_sha)
            except github.RateLimitExceededException:
                if self.g.get_rate_limit().core.remaining == 0:
                    # loop again with a new token
                    self.g = self._get_github_caller()
                    continue
            except github.UnknownObjectException:
                raise GitHubAPIUnknownObject

            self.review_category = None
            self.github_pull_requests = []

            try:
                self._check_code_review()
                return
            except github.RateLimitExceededException:
                if self.g.get_rate_limit().core.remaining == 0:
                    # loop again with a new token
                    self.g = self._get_github_caller()
            except github.UnknownObjectException:
                raise GitHubAPIUnknownObject

    def _get_github_caller(self):
        token = os.environ["GITHUB_TOKEN"]
        try:
            tokens = json.loads(token)
            for k in tokens.keys():
                g = Github(tokens[k])
                if g.get_rate_limit().core.remaining > 0:
                    return g
            raise AllGitHubTokensRateLimitExceeded
        except:
            return Github(token)

    def _check_code_review(self):
        checkers = [
            self.github_pr,
            self.gerrit_review,
            self.different_committer,
        ]

        for check in checkers:
            check()
            if self.review_category:
                break

    def github_pr(self):
        for pr in self.github_commit.get_pulls():
            self.github_pull_requests.append(pr)
            if pr.get_reviews().totalCount > 0:
                self.review_category = CodeReviewCategory.GitHubReview
            elif pr.user and pr.merged_by and pr.user.login != pr.merged_by.login and pr.merged_by.login != GITHUB:
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
