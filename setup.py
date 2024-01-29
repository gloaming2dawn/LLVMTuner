from setuptools import setup, find_packages

setup(
    name="llvmtuner",
    version="0.0.3",
    author="Jiayu Zhao",
    python_requires=">=3.7",
    packages=find_packages(),#["llvmtuner"]
    install_requires=['numpy'],
    zip_safe=False,
    entry_points = {
        'console_scripts': ['clangopt=llvmtuner.clangopt:main'],
    }
)