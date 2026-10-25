import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tests never talk to the real LLM: a dummy key keeps config valid, and generate_json is mocked.
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session", autouse=True)
def fixtures():
    if not (FIXTURES / "sample_resume.pdf").exists():
        from tests.make_fixtures import main

        main()
    return FIXTURES
