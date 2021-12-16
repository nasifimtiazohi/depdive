from depdive.repository_diff import get_repository_file_list
import tempfile
from git import Repo


def test_repository_file_list():
    repository = "https://github.com/nasifimtiazohi/package-locator"
    commit = "8ba11d8904971c53e9a7fe6522ed148a3b9e6c45"

    with tempfile.TemporaryDirectory() as temp_dir:
        Repo.clone_from(repository, temp_dir)
        files = get_repository_file_list(temp_dir, commit)
        assert len(files) == 82
        assert "package_locator/locator.py" not in files
