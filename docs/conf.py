# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Pyquizhub'
copyright = '2025, Ivan Tambovtsev'
author = 'Ivan Tambovtsev'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',  # Core Sphinx extension for auto-documentation
    'sphinx.ext.napoleon',  # Support for Google/NumPy style docstrings
    'sphinx.ext.viewcode',  # Add links to highlighted source code
    'sphinx.ext.coverage',  # Check documentation coverage
    'sphinx_autodoc_typehints',  # Support for Python type hints
    'sphinx.ext.autosummary',  # Auto-generate summary tables
    'sphinx.ext.intersphinx',  # Link to other projects' documentation
    'sphinx.ext.githubpages',  # Publish to GitHub Pages
    'sphinx.ext.todo',  # Support for todo items
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'  # Using Read the Docs theme
html_static_path = ['_static']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# AutoDoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Auto-generate API documentation
autosummary_generate = True
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autoclass_content = 'both'

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'fastapi': ('https://fastapi.tiangolo.com', None),
}

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'
