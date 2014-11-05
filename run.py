#Version-safe import of the 'print()' function
from __future__ import print_function
import argparse
import os
import logging
import subprocess
import shutil
import sys

# List of packages needed when building sources for pyjen
REQUIREMENTS = ['requests', 'wheel', 'sphinx', 'pytest', 'pytest-cov', 'radon', 'pylint']

# Folder where log files will be stored
log_folder = os.path.abspath(os.path.join(os.path.curdir, "logs"))

# Used to output detailed output to the logger that isn't just simply for
# informational purpose but yet not as verbose as full debugging output.
VERBOSE_LOGGING_LEVEL=15

# Set a global logger for use by this script
modlog = logging.getLogger('pyjen').addHandler(logging.NullHandler())

def _prepare_env():
    """Adds all PyJen dependencies to the Python runtime environment used to call this script

    Uses the global REQUIREMENTS list to install packages
    """
    try:
        import pip
    except ImportError:
        pip_url = "http://pip.readthedocs.org/en/latest/installing.html"
        modlog.error("PIP package not installed. See this website for details on how to install it: " + pip_url)
        return

    #Using pip, see what packages are currently installed
    installed_packages = pip.get_installed_distributions()
    required_packages = REQUIREMENTS

    #Now, remove any currently installed packages from our list of dependencies
    for i in installed_packages:
        if i.key in required_packages:
            required_packages.remove(i.key)
    
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
        return

    modlog.info("dependencies installed successfully")


def _make_package():
    """Creates the redistributable package for the PyJen project"""
    import re

    # delete any pre-existing packages
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    # create new package
    modlog.info("creating package...")

    result = subprocess.check_output(["python", "setup.py", "bdist_wheel"],
                                     stderr=subprocess.STDOUT, universal_newlines=True)
    modlog.debug(result)

    # delete intermediate folders
    shutil.rmtree("build")

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
    result = subprocess.check_output(["python", "setup.py", "bdist_wheel", "upload"], stderr=subprocess.STDOUT, universal_newlines=True)
    modlog.debug(result)

    # todo: publish documentation
    # 	ncftpput -R -v -m pyjentfc /PyJen ./docs/build/html/*


def _code_analysis():
    pyjen_path = os.path.join(os.path.curdir, "pyjen")
    cmd = ["pylint", "--rcfile=.pylint", "-f", "parseable", "pyjen"]
    result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
    lint_log_filename = os.path.join(log_folder, "pylint.log")
    lint_log_file = open(lint_log_filename)
    lint_log_file.write(result)
    lint_log_file.close()
    
    # first generate cyclomatic complexities for source files in XML format for integration with external tools
    result = subprocess.check_output(["radon", "cc", "-sa", "--xml", pyjen_path], stderr=subprocess.STDOUT, universal_newlines=True)
    complexity_log_filename = os.path.join(log_folder, "radon_complexity.xml")
    complexity_log_file = open(complexity_log_filename)
    complexity_log_file.write(result)
    complexity_log_file.close()
    
    # next run all code analysers against all source files
    stats_log_filename = os.path.join(log_folder, "stats.log")
    modlog.debug("Creating code analysis log file " + stats_log_filename)
    stats_log = open(stats_log_filename, "w")

    for (folder, subfolders, files) in os.walk(pyjen_path):
        for cur_file in files:
            cur_file_full_path = os.path.join(folder, cur_file)
            result = subprocess.check_output(["radon", "cc", "-sa", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            modlog.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)
            result = subprocess.check_output(["radon", "raw", "-s", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            modlog.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)
            result = subprocess.check_output(["radon", "mi", "-s", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            modlog.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)

    stats_log.close()
    
def _run_tests():
    # todo: run unit tests
    #py.test --cov-report term-missing --cov pyjen -s ./unit_tests/test*.py --verbose --junit-xml test_results.xml > "$log_folder/pytest.log" 2>&1
    params = ["py.test", "--cov-report", "term-missing", "--cov pyjen", "-s", r".\unit_tests", "--verbose", "--junit-xml", "test_results.xml"]
    result = subprocess.check_output(params, stderr=subprocess.STDOUT, universal_newlines=True)
    modlog.log(VERBOSE_LOGGING_LEVEL, result)
    # todo see if we are asked to run functional tests and run them
    #py.test --cov-report term-missing --cov pyjen -s ./functional_tests/*tests.py --verbose --junit-xml test_results.xml > "$log_folder/func_pytest.log" 2>&1
    pass


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
    file_logger = logging.FileHandler(log_file)
    file_logger.setFormatter("%(asctime)s %(levelname)s:%(message)s")
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
    _parser = argparse.ArgumentParser( description='PyJen source project configuration utility')
    
    _parser.add_argument('-e', '--prep_env', action='store_true', help='Install all Python packages used by PyJen sources')
    _parser.add_argument('-p', '--package', action='store_true', help='Generate redistributable package for PyJen')
    _parser.add_argument('--stats', action='store_true', help='Run static code analysis again PyJen sources')
    _parser.add_argument('--publish', action='store_true', help='Publish release artifacts online to PyPI')
    _parser.add_argument('--unittest', action='store_true', help='Runs unit test suite for the project')
    #_parser.add_argument('--functest', action='store_true', help='Runs functional test suite for the project')

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

    if args.package:
        _make_package()


    if args.stats:
        modlog.info("Running code analysis tools...")
        _code_analysis()
        modlog.info("Code analysis complete")

    if args.publish:
        modlog.info("publishing release...")
        _publish()
        modlog.info("release published successfully")

    if args.unittest:
        modlog.info("running unit tests...")
        _run_tests()
        modlog.info("finished running tests")