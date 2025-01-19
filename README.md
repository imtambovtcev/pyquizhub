# PyQuizHub
![logo](image/README/logo.png)
PyQuizHub is a flexible quiz management system with a modular architecture that consists of:

* Core Engine - Handles quiz logic and data management
* Storage Backends - Supports multiple storage options
* Access Adapters - Provides different access levels and interaction methods

## Features

- **Admin**: Full system access and configuration
- **Creator**: Can create and manage quizzes
- **User**: Can take quizzes using access tokens

## Getting Started

To get started with PyQuizHub, follow the instructions in the [documentation](docs/index.rst).

## Installation

You can install PyQuizHub using [Poetry](https://python-poetry.org/):

```bash
poetry install
```

## Running the Application

To run the application, use the following command:

```bash
poetry run uvicorn pyquizhub.main:app --reload
```

## Testing

To run the tests, use the following command:

```bash
poetry run pytest
```

## Documentation

The documentation is generated using [Sphinx](https://www.sphinx-doc.org/). To build the documentation, use the following command:

```bash
poetry run sphinx-build -b html docs/ docs/_build/html
```

## License

This project is licensed under the MIT License.