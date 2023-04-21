from setuptools import setup, find_packages

setup(
    name="lsp_tree_finder",
    version="0.1.0",
    packages=find_packages(),
    package_dir={
        'tree-sitter-php': '/vendor/tree-sitter-php',
        'pylspclient_silet': '/vendor/pylspclient_silet',
        },
    install_requires=[
        "tree_sitter",
    ],
    entry_points={
        "console_scripts": [
            "lsp-tree-finder=lsp_tree_finder.main:cli",
        ],
    },
)
