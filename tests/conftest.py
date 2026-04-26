import pytest
import pypandoc


def pytest_configure(config):
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        pytest.exit(
            "pandoc is not installed. Please install it: sudo apt install pandoc",
            returncode=1,
        )
