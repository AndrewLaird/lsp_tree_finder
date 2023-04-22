from setuptools import setup, find_packages

setup(
    name="lsp_tree_finder",
    version="0.1.0",
    packages=find_packages(),
    package_dir={
        'tree-sitter-php': '/vendor/tree-sitter-php',
    },
    install_requires=[
        "tree_sitter",
    ],
    dependency_links=[
        # Up to date pylspclient
        "git+https://github.com/yeger00/pylspclient.git#egg=pylspclient'"
    ],
    entry_points={
        "console_scripts": [
            "lsp-tree-finder=lsp_tree_finder.main:cli",
        ],
    },
)
