import random
import string


def generate_token(length=16):
    """Generate a short, random, alphanumeric token."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
