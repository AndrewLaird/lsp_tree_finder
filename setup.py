from setuptools import setup, find_packages

setup(
    name="lsp_tree_finder",
    version="0.1.0",
    packages=find_packages(),
    package_data={
        '': ['*.c', '*.h'],  # This will include all .c and .h files in the package
        'tree-sitter-php': ['vendor/tree-sitter-php/**/*'],
    },
    install_requires=[
        "tree_sitter",
        "pylspclient",
    ],
    entry_points={
        "console_scripts": [
            "lsp-tree-finder=lsp_tree_finder.main:cli",
        ],
    },
)
