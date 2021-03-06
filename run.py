#Version-safe import of the 'print()' function
from __future__ import print_function
import argparse
import os
import logging
import subprocess
import shutil
import sys

# List of packages needed when building sources for pyjen
REQUIREMENTS = ['requests>=2.0.1', 'six', 'wheel', 'sphinx>=1.2.3', 'pytest', 'pytest-cov', 'mock', 'radon', 'pylint']

# Folder where log files will be stored
log_folder = os.path.abspath(os.path.join(os.path.curdir, "logs"))

# Set a global logger for use by this script
modlog = logging.getLogger('pyjen')
modlog.addHandler(logging.NullHandler())

def _version_string_to_tuple(version):
    """Helper function that converts a version number from string format to a tuple

    :return: tuple of version numbers
    :rtype: :func:`tuple`
    """
    return tuple([int(i) for i in version.split(".")])
    pass

def _version_tuple_to_string(version):
    """Helper function that converts a version number from a tuple to string format

    :return: string representation of a version tuple
    :rtype: :func:`str`
    """
    return ".".join(list(map(str, version)))

def _get_package_version(package_name):
    """Helper function that returns the version number for a given Python package

    :param str package_name: the name of the package to query
    :return: The version of the given package as a tuple
    :rtype: :func:`tuple`
    """
    import pip
    installed_packages = pip.get_installed_distributions()
    for i in installed_packages:
        if i.key.lower() == package_name.lower():
            return _version_string_to_tuple(i.version)

    raise RuntimeError("Missing required package " + package_name)

def _split_requirement(package_requirement):
    """Helper function to extract the package name and required version from a package string

    :param str package_requirement: package requirement string, typically including a name and optional
        required version number, of the form 'package_name >= 1.2.3'
    :return: The name of the required package and its supported version number
    :rtype: :class:`tuple`
    """
    import re
    temp = re.split("<|>|=", package_requirement)
    package_name = temp[0]
    if len(temp) > 1:
        package_version = _version_string_to_tuple(temp[-1])
    else:
        package_version = ()

    return package_name, package_version

def _find_missing_packages():
    """Helper function that generates a list of packages that need to be installed

    :return: list of 0 or more packages that need to be installed
    :rtype: :class:`list`
    """
    import pip

    #Using pip, see what packages are currently installed
    installed_packages = pip.get_installed_distributions()
    required_packages = REQUIREMENTS

    #Now, remove any currently installed packages from our list of dependencies
    for ip in installed_packages:
        for rp in required_packages:
            (name, version) = _split_requirement(rp)
            if ip.key == name:
                if _version_string_to_tuple(ip.version) >= version:
                    required_packages.remove(rp)
        if len(required_packages) == 0:
            return []

    return required_packages

def _prepare_env():
    """Adds all PyJen dependencies to the Python runtime environment used to call this script

    Uses the global REQUIREMENTS list to install packages
    """
    try:
        import pip
    except ImportError:
        pip_url = "http://pip.readthedocs.org/en/latest/installing.html"
        modlog.error("PIP package not installed. See this website for details on how to install it: " + pip_url)
        exit(1)

    required_packages = _find_missing_packages()

    if len(required_packages) == 0:
        modlog.info("All required dependencies already installed")
        return

    modlog.info("Installing the following new packages: " + str(required_packages))

    # Construct a list of arguments to pass to the PIP tool
    pip_args = []

    #See if any web proxy is enabled on the system an use it if found
    if 'http_proxy' in os.environ:
        proxy = os.environ['http_proxy']
        pip_args.append('--proxy')
        pip_args.append(proxy)
        modlog.info("Using the following proxy server: " + proxy)

    # Setup install command to install all missing packages
    pip_args.append('install')

    for req in required_packages:
        pip_args.append(req)

    # Configure PIP to do a silent install to avoid overly verbose output on the command line
    pip_args.append('--quiet')

    # Then, redirect all output to log files for later auditing
    pip_log_file = os.path.join(log_folder, "pip_install.log")
    if os.path.exists(pip_log_file):
        os.remove(pip_log_file)
    pip_args.append('--log')
    pip_args.append(pip_log_file)

    pip_error_log = os.path.join(log_folder, "pip_error.log")
    pip_args.append('--log-file')
    pip_args.append(pip_error_log)

    # Finally, run the installation process
    modlog.info('installing dependencies...')
    try:
        pip.main(initial_args=pip_args)
    except:
        modlog.info("Error installing packages. See {0} for details.".format(pip_error_log))
        exit(1)

    modlog.info("dependencies installed successfully")


def _show_version():
    """Shows the PyJen version number"""
    from pyjen import __version__
    modlog.info("PyJen Version " + __version__)


def _make_package():
    """Creates the redistributable package for the PyJen project"""
    import re

    # delete any pre-existing packages
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    # create new package
    modlog.info("creating package...")

    try:
        result = subprocess.check_output(["python", "setup.py", "bdist_wheel"],
                                     stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to generate wheel file ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    modlog.debug(result)

    # delete intermediate folders
    shutil.rmtree("build")
    shutil.rmtree("pyjen.egg-info")

    #sanity check: make sure wheel file exists
    package_contents = os.listdir("dist")
    if len(package_contents) > 1:
        modlog.warning("Multiple files detected in package folder. Only one .whl file expected.")

    wheel_file_found = False
    wheel_file_pattern = r"^pyjen.*-py2.py3-none-any.whl$"
    for obj in package_contents:
        file_path = os.path.join(os.getcwd(), "dist", obj)
        if os.path.isfile(file_path) and re.search(wheel_file_pattern, obj) is not None:
            wheel_file_found = True

    if not wheel_file_found:
        modlog.error("Expected output file (.whl) not found in ./dist folder.")
        sys.exit(1)

    #todo: test package
    #pushd functional_tests > /dev/null
    #./package_tests.sh

    modlog.info("package created successfully")


def _publish():
    """Publishes a PyJen release to PyPi"""
    modlog.info("publishing release...")

    try:
        result = subprocess.check_output(["python", "setup.py", "bdist_wheel", "upload"],
                                     stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to publish new PyJen release ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    modlog.debug(result)

    # todo: after the publish completes, auto-update the version number
    # todo: lay tag on release
    modlog.info("release published successfully")


def _code_analysis():
    """Generates code analysis reports and metrics on the PyJen sources"""
    modlog.info("Running code analysis tools...")

    # PyLint code analysis
    from pylint import epylint as lint

    # now we generate a pylint report in HTML format
    params = 'pyjen -f html'
    with open(os.path.join(log_folder, "pylint.html"), "w") as std:
        with open(os.path.join(log_folder, "pylint_html_err.log"), "w") as err:
            lint.py_run(params, stdout=std, stderr=err, script="pylint")

    # next we generate a pylint report in 'parseable' format, for use on build automation
    params = 'pyjen'
    with open(os.path.join(log_folder, "pylint.txt"), "w") as std:
        with open(os.path.join(log_folder, "pylint_plain_err.log"), "w") as err:
            lint.py_run(params, stdout=std, stderr=err, script="pylint")

    modlog.info("Lint analysis can be found in ./" + os.path.relpath(log_folder, os.getcwd()) + "/pylint.html")

    # generate cyclomatic complexities for source files in XML format for integration with external tools
    pyjen_path = os.path.join(os.getcwd(), "pyjen")
    try:
        result = subprocess.check_output(["radon", "cc", "-sa", "--xml", pyjen_path],
                                     stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to calculate cyclomatic complexity ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    complexity_log_filename = os.path.join(log_folder, "radon_complexity.xml")
    with open(complexity_log_filename, "w") as complexity_log_file:
        complexity_log_file.write(result)

    # next run all code analysers against all source files
    stats_log_filename = os.path.join(log_folder, "stats_cc.log")
    with open(stats_log_filename, "w") as stats_log:
        for (folder, subfolders, files) in os.walk(pyjen_path):
            for cur_file in files:
                if os.path.splitext(cur_file)[1] == ".py":
                    cur_file_full_path = os.path.join(folder, cur_file)
                    try:
                        result = subprocess.check_output(["radon", "cc", "-sa", cur_file_full_path],
                                                     stderr=subprocess.STDOUT, universal_newlines=True)
                    except subprocess.CalledProcessError as err:
                        modlog.error("Failed to calculate cyclomatic complexity ({0})".format(err.returncode))
                        modlog.error(err.output)
                        exit(1)
                    modlog.debug(result)
                    stats_log.write(result)

    stats_log_filename = os.path.join(log_folder, "stats_raw.log")
    with open(stats_log_filename, "w") as stats_log:
        for (folder, subfolders, files) in os.walk(pyjen_path):
            for cur_file in files:
                if os.path.splitext(cur_file)[1] == ".py":
                    cur_file_full_path = os.path.join(folder, cur_file)
                    try:
                        result = subprocess.check_output(["radon", "raw", "-s", cur_file_full_path],
                                                     stderr=subprocess.STDOUT, universal_newlines=True)
                    except subprocess.CalledProcessError as err:
                        modlog.error("Failed to calculate raw code statistics ({0})".format(err.returncode))
                        modlog.error(err.output)
                        exit(1)
                    modlog.debug(result)
                    stats_log.write(result)

    stats_log_filename = os.path.join(log_folder, "stats_mi.log")
    with open(stats_log_filename, "w") as stats_log:
        for (folder, subfolders, files) in os.walk(pyjen_path):
            for cur_file in files:
                if os.path.splitext(cur_file)[1] == ".py":
                    cur_file_full_path = os.path.join(folder, cur_file)
                    try:
                        result = subprocess.check_output(["radon", "mi", "-s", cur_file_full_path],
                                                     stderr=subprocess.STDOUT, universal_newlines=True)
                    except subprocess.CalledProcessError as err:
                        modlog.error("Failed to calculate maintainability index ({0})".format(err.returncode))
                        modlog.error(err.output)
                        exit(1)
                    modlog.debug(result)
                    stats_log.write(result)

    modlog.info("Radon analysis can be found here: ./" + os.path.relpath(log_folder, os.getcwd()) + "/stats*.log")
    modlog.info("Code analysis complete")


def _run_tests(RunFuncTests):
    """Runs all PyJen tests

    Generates reports about test coverage and such, storing the results in to disk

    :param bool RunFuncTests: indicates whether the functional tests should be run as well as the unit tests
    """
    modlog.info("running unit tests...")

    import pytest

    # TODO: Customize parameters based on user input, like verbosity level which shows all tests and reports
    #       ie: --cov-report term-missing, -r xEXw
    test_params = ["./unit_tests"]
    if RunFuncTests:
        test_params.append("./functional_tests")
    test_params.extend(["-s", "-q",
                   "--cov-report", "html", "--cov-report", "xml", "--cov", "pyjen", "--no-cov-on-fail",
                   "--junit-xml", "test_results.xml"])
    #TODO: Find a way to suppress remaining output generated by this call
    pytest.main(test_params)

    modlog.info("finished running tests")

def _make_docs():
    """Generates the online documentation for the project"""
    # TODO: See if we can rework this function to avoid using the batch file (ie: call sphinx directly)

    modlog.info("Generating API documentation...")

    import sys
    if (3, 0) <= sys.version_info[:2] < (3, 3):
        p_ver = _version_tuple_to_string(sys.version_info[:3])
        modlog.info("Sphinx documentation tool does not support Python v{0}".format(p_ver))
        exit(1)

    if _get_package_version("Sphinx") < (1, 2, 3):
        modlog.error("Unsupported Sphinx version detected: " + _get_package_version("Sphinx"))
        modlog.error("Please run the --prep_env operation to property configure your environment.")
        exit(1)

    # Purge any previous build artifacts
    # TODO: Rework this to call 'make clean' from the command line
    doc_dir = os.path.join(os.getcwd(), "docs")
    build_dir = os.path.join(doc_dir, "build")
    #if os.path.exists(build_dir):
    #    shutil.rmtree(build_dir)

    # First generate the documentation build scripts
    #       -f  force overwrite of output files
    #       -e  separate each module to its own page
    try:
        result = subprocess.check_output(["sphinx-apidoc", "-f", "-e", "-o", "./docs/source", "pyjen"],
                                         stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to generate API docs ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    modlog.debug(result)

    # Then generate the actual content
    cur_dir = os.getcwd()
    os.chdir(doc_dir)
    if os.name == 'nt':
        params = ["make.bat"]
    else:
        params = ["make"]
    params.append("html")
    try:
        result = subprocess.check_output(params, stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to generate documentation ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    modlog.debug(result)
    os.chdir(cur_dir)

    # for extra verification, lets generate a sample PyPI homepage as well
    from docutils.core import publish_string
    try:
        homepage_content = subprocess.check_output(["python", "setup.py", "--long-description"],
                                               stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as err:
        modlog.error("Failed to generate sample PyPi homepage ({0})".format(err.returncode))
        modlog.error(err.output)
        exit(1)
    homepage_html = publish_string(homepage_content, writer_name='html')
    with open("pypi_homepage.html", "w") as outfile:
        outfile.write(homepage_html.decode("utf-8"))

    # TODO: Find a way to do some basic verification on the documentation output
    modlog.info("Documentation complete")


def _configure_logger():
    """Configure the custom logger for this script

    All info messages and higher will be shown on the console
    All messages from all priorities will be streamed to a log file
    """
    global modlog
    modlog = logging.getLogger("pyjen")
    modlog.setLevel(logging.DEBUG)

    # Primary logger will write all messages to a log file
    log_file = os.path.join(log_folder, "run.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    file_logger = logging.FileHandler(log_file)
    file_logger_format = "%(asctime)s %(levelname)s:%(message)s"
    file_formatter = logging.Formatter(file_logger_format)
    file_logger.setFormatter(file_formatter)
    file_logger.setLevel(logging.DEBUG)

    modlog.addHandler(file_logger)

    # Secondary logger will show all 'info' class messages and below on the console
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    
    console_log_format = "%(asctime)s: %(message)s"
    console_formatter = logging.Formatter(console_log_format)
    console_formatter.datefmt = "%H:%M"
    console_logger.setFormatter(console_formatter)

    modlog.addHandler(console_logger)

    
def _get_args():
    """Configure the command line parser and online help systems

    :returns: set of parameters provided by the user on the command line
    """
    _parser = argparse.ArgumentParser(description='PyJen source project configuration utility')

    _parser.add_argument('-v', '--version', action='store_true', help='Display the PyJen version number')
    _parser.add_argument('-e', '--prep_env', action='store_true', help='Install all Python packages used by PyJen sources')
    _parser.add_argument('-p', '--package', action='store_true', help='Generate redistributable package for PyJen')
    _parser.add_argument('-s', '--stats', action='store_true', help='Run static code analysis again PyJen sources')
    _parser.add_argument('-u', '--publish', action='store_true', help='Publish release artifacts online to PyPI')
    _parser.add_argument('-t', '--test', action='store_true', help='Runs the suite of unit tests and generates metrics about the tests')
    _parser.add_argument('-f', '--functional_test', action='store_true', help='Runs the more time consuming functional test suite')
    _parser.add_argument('-d', '--docs', action='store_true', help='Generate online documentation for the project')
    # TODO: Consider using this to invoke a function when option is specified: parser.set_defaults(function)

    # If no command line arguments provided, display the online help and exit
    if len(sys.argv) == 1:
        _parser.print_help()
        sys.exit(0)
        
    _args = _parser.parse_args()
    modlog.debug("Command line params: " + str(_args))
    
    return _args


if __name__ == "__main__":
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    _configure_logger()
    
    args = _get_args()

    if args.prep_env:
        _prepare_env()

    if args.version:
        _show_version()

    if args.test or args.functional_test:
        _run_tests(args.functional_test)

    if args.package:
        _make_package()

    if args.docs:
        _make_docs()

    if args.stats:
        _code_analysis()

    if args.publish:
        _publish()
