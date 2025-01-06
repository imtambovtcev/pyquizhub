import random
import string


def generate_token(length=16):
    """Generate a short, random, alphanumeric token."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_quiz_token():
    """Generate a quiz token."""
    return generate_token(16)


def generate_quiz_id(quiz_name=''):
    """Generate a quiz ID from the quiz name."""
    if quiz_name is None:
        quiz_name = ''
    # Remove non-alphanumeric characters and convert to uppercase
    uniform_name = ''.join(filter(str.isalnum, quiz_name)).upper()
    # Limit to max 10 characters
    uniform_name = uniform_name[:10]
    # Generate a random token to complete the ID to 16 characters
    random_token = generate_token(16 - len(uniform_name))
    return uniform_name + random_token
