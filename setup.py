from setuptools import setup
import io
import re
import os


here = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(here, "json_convert.py")

with io.open(version_file, "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.M)
if not match:
    raise RuntimeError("Unable to find APP_VERSION in json_convert.py")
package_version = match.group(1)

setup(
    name="battinfo_converter",
    version=package_version,
    # Declare the package name you'll import, and point it at the current dir
    packages=["battinfo_converter"],
    package_dir={"battinfo_converter": "."},
    install_requires=[
        "pandas",
        "streamlit",
    ],
)
