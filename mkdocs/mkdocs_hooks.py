import logging


# Suppress griffe "no type annotation" warnings until type hints are added.
# Revisit when Python 3.14 type system improvements land.
logging.getLogger("mkdocs.plugins.griffe").setLevel(logging.ERROR)
