# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
# to get around sbs import errors
#sys.path.insert(0, os.path.abspath('../mock'))
from mock import mock_sbs as sbs


# -- Project information -----------------------------------------------------

project = 'SBS Utils'
copyright = '2022, Doug Reichard'
author = 'Doug Reichard'

# The full version, including alpha/beta/rc tags
release = '1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx_tabs.tabs'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

graphviz_dot="F:\\t\\graphviz\\bin\\dot.exe"

from pygments.lexer import RegexLexer
from pygments.token import *

class MastLexer(RegexLexer):
    name = 'Mast'
    aliases = ['mast']
    filenames = ['*.mast']

    tokens = {
        'root': [
            (r' .*\n', Text),
            (r'\+.*\n', Generic.Inserted),
            (r'-.*\n', Generic.Deleted),
            (r'@.*\n', Generic.Subheading),
            (r'Index.*\n', Generic.Heading),
            (r'=.*\n', Generic.Heading),
            (r'.*\n', Text),
        ]
    }


def setup(app):
   app.add_lexer('mast', MastLexer)