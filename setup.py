from setuptools import setup, find_packages
import io, re, os

# Path to your package
here = os.path.abspath(os.path.dirname(__file__))

# Read the file and extract APP_VERSION
version_file = os.path.join(here, "json_convert.py")
with io.open(version_file, "r", encoding="utf-8") as f:
    content = f.read()

# Regex out the APP_VERSION
# This has to be done because reading from the file is safer than directly import the module. 
version_match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.M)
if not version_match:
    raise RuntimeError("Unable to find APP_VERSION in json_convert.py")
package_version = version_match.group(1)

setup(
    name="battinfo_converter",
    version=package_version,            # dynamically read from json_convert.py
    packages=find_packages(),
    install_requires=[
        "pandas",
        "streamlit",
    ],
)