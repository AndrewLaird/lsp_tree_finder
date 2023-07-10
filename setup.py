from setuptools import setup, find_packages, Command
from setuptools.command.install import install
from pathlib import Path
from tree_sitter import Language

class BuildLanguagesCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        Language.build_library(
            # Store the library in the `build` directory
            str(Path(__file__).parent / "src/lsp_tree_finder/build/my-languages.so"),

            # Include one or more languages
            [
                str(Path(__file__).parent / "tree-sitter-php"),
            ],
        )

class InstallCommand(install):
    def run(self):
        self.run_command('build_languages')
        install.run(self)
setup(
    name='lsp_tree_finder',
    version='0.2',
    url='https://github.com/AndrewLaird/lsp_tree_finder',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    author='Andrew Laird',
    author_email='lairdandrew11@gmail.com',
    description='Command line tool to search for pattern inside of call tree under selected function',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'numpy',
        'matplotlib',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    entry_points={
        'console_scripts': [
            'lsp_tree_finder=lsp_tree_finder.main:cli',
        ],
    },
    cmdclass={
        'build_languages': BuildLanguagesCommand,
        'install': InstallCommand,
    },
)
