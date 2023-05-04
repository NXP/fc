# Configuration file for the Sphinx documentation builder.

# -- Project information

import subprocess

project = 'FC'
copyright = '2021-2023, NXP, Larry Shen'
author = 'Larry Shen'

version = (
    subprocess.Popen(
        ["cat", "fc_common/VERSION"], cwd=r"..", stdout=subprocess.PIPE
    )
    .stdout.read()
    .rstrip()
    .decode("utf-8")
)
release = version

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.imgconverter',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for EPUB output

epub_show_urls = 'footnote'

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

html_logo = 'images/fc.png'

html_theme_options = {
    'collapse_navigation': False,
}

html_static_path = ['css']

html_css_files = [
    'css-style.css',
]
