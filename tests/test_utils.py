def test_generate_token():
    from pyquizhub.utils import generate_token
    token = generate_token()
    assert len(token) == 16
    assert token.isalnum()


def test_generate_quiz_token():
    from pyquizhub.utils import generate_quiz_token
    quiz_token = generate_quiz_token()
    assert len(quiz_token) == 16
    assert quiz_token.isalnum()


def test_generate_quiz_id():
    from pyquizhub.utils import generate_quiz_id
    quiz_id = generate_quiz_id("Sample Quiz")
    assert quiz_id.startswith("SAMPLEQUIZ")
    assert len(quiz_id) == 16
    assert quiz_id.isalnum()

    quiz_id = generate_quiz_id(
        "A Very Long Quiz Name That Exceeds Ten Characters")
    assert quiz_id.startswith("AVERYLONGQ")
    assert len(quiz_id) == 16
    assert quiz_id.isalnum()

    quiz_id = generate_quiz_id("")
    assert len(quiz_id) == 16
    assert quiz_id.isalnum()
