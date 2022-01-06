from git import repo
from github import Github
import os
from enum import Enum

class CodeReviewCategory(Enum):
    GitHubReview = 1
    DifferentMerger = 2
    GerritReview = 3
    ProwReview = 4


class GitHubReviewInfo:
    def __init__(self, login, state, association, date) -> None:
        self.login: str = login
        self.state: str = state
        self.association: str = association
        self.date: str = date

class NotGitHubRepo(Exception):
    pass

def get_github_repo_full_name(repository):
    s ='github.com/'
    s = repository[repository.find(s) + len(s):]
    return '/'.join(s.split('/')[:2])

class CommitReviewInfo:
    def __init__(self, repository, commit_sha):
        if 'github' not in repository:
            raise NotGitHubRepo
        #TODO: check if a mirror from about section

        self.repo_full_name = get_github_repo_full_name(repository)
        self.commit_sha = commit_sha

        self.review_category = None
        self.github_pull_requests = []

        checkers = [self.github_code_review, self.gerrit_code_review]
        for check in checkers:
            check()
            if self.review_category:
                break

    def github_code_review(self):
        g = Github(os.environ["GITHUB_TOKEN"])
        repo = g.get_repo(self.repo_full_name)
        commit = repo.get_commit(self.commit_sha)

        for pr in commit.get_pulls():
            self.github_pull_requests.append(pr)
            if pr.get_reviews().totalCount > 0:
                self.review_category = CodeReviewCategory.GitHubReview
            elif commit.author.login != pr.merged_by.login:
                self.review_category = CodeReviewCategory.DifferentMerger
            elif any([l.name in ["lgtm", "approved"] for l in pr.get_labels()]):
                self.review_category = CodeReviewCategory.ProwReview

    def gerrit_code_review(self):
        g = Github(os.environ["GITHUB_TOKEN"])
        repo = g.get_repo(self.repo_full_name)
        commit = repo.get_commit(self.commit_sha)
        message = commit.commit.message
        if "https://review" in message and "\nReviewed-by: " in message:
            self.review_category = CodeReviewCategory.GerritReview
