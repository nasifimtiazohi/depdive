from github import Github
import os
from datetime import datetime
from enum import Enum

# g = Github(os.environ['GITHUB_TOKEN'])


# repo = g.get_repo("tokio-rs/tokio")
# commit = repo.get_commit("5739d6dcf484b4aa6b539ac018d354937ad33359")
# author = commit.author
# print(author, commit.committer)
# print(help(author))
# code_reviewed = False
# for pr in commit.get_pulls():
#     # Check GitHub review status
#     for reviewe in pr.get_reviews():
#         # TODO: see if anyone has approved?
#         code_reviewed = True

#     merge_commit = repo.get_commit(pr.merge_commit_sha)
#     print(pr.merged_by)
#     print(merge_commit)
#     print(merge_commit.committer)

# repo = g.get_repo("lodash/lodash")
# commit = repo.get_commit("4c2e40e7a2fc5e40d4962afad0ea286dfb963da7")
# author = commit.author
# print(author, commit.committer)
# code_reviewed = False
# for pr in commit.get_pulls():
#     # Check GitHub review status
#     for reviewe in pr.get_reviews():
#         # TODO: see if anyone has approved?
#         code_reviewed = True

#     merge_commit = repo.get_commit(pr.merge_commit_sha)
#     print(pr.merged_by)
#     print(merge_commit)
#     print(merge_commit.committer)

# repo = g.get_repo("diem/diem")
# commit = repo.get_commit("61a5eb9039aa007eb46546426beab0ea7a9e549a")
# author = commit.author
# print(author, commit.committer)
# code_reviewed = False
# for pr in commit.get_pulls():
#     # Check GitHub review status
#     for reviewe in pr.get_reviews():
#         # TODO: see if anyone has approved?
#         code_reviewed = True

#     merge_commit = repo.get_commit(pr.merge_commit_sha)
#     print(pr.merged_by)
#     print(merge_commit)
#     print(merge_commit.committer)

class CodeReviewReason(Enum):
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

class GitHubPullRequests:
    def __init__(self, author, merger) -> None:
        self.author = author
        self.merger = merger
        
        self.reviewed = None
        self.reviews = []


class CommitCodeCommitInfo:
    def __init__(self, repo_full_name, commit_sha):
        self.repo_full_name = repo_full_name
        self.commit_sha = commit_sha
        
        self.reviewed = None
        self.reason = None

        self.github_pull_requests = []

        self.github_code_review()
    
    def github_code_review(self):
        g = Github(os.environ['GITHUB_TOKEN'])
        repo = g.get_repo(self.repo_full_name)
        commit = repo.get_commit(self.commit_sha)

        for pr in commit.get_pulls():
            github_pr = GitHubPullRequests()
            github_pr.author = commit.author.login
            github_pr.merger = pr.merged_by.login
            for review in pr.get_reviews():
                self.reviewed = True
                self.reason = CodeReviewReason.GitHubReview
                self.github_reviews.append(
                    GitHubReviewInfo(
                        review.user.login,
                        review.state,
                        review.raw_data['author_association'],
                        review.submitted_at,
                    )
                )




CommitCodeCommitInfo("tokio-rs/tokio", "5739d6dcf484b4aa6b539ac018d354937ad33359")