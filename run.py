#Version-safe import of the 'print()' function
from __future__ import print_function
import argparse
import os
import logging
import subprocess
import shutil
import pip
import sys

# List of packages needed when building sources for pyjen
REQUIREMENTS = ['requests', 'wheel', 'sphinx', 'pytest', 'pytest-cov', 'radon', 'pylint']

# Folder where log files will be stored
log_folder = os.path.abspath(os.path.join(os.path.curdir, "logs"))

# Used to output detailed output to the logger that isn't just simply for
# informational purpose but yet not as verbose as full debugging output.
VERBOSE_LOGGING_LEVEL=15

def _prepare_env():
    #Using pip, see what packages are currently installed
    installed_packages = pip.get_installed_distributions()
    
    #Now, remove any currently installed packages from our list of dependencies
    for i in installed_packages:
        if i.key in REQUIREMENTS:
            REQUIREMENTS.remove(i.key)
    
    if len(REQUIREMENTS) == 0:
        return
    
    #Finally, install any missing dependencies
    pip_args = ['-vvv']
    
    #See if any web proxy is enabled on the system an use it if found
    if 'http_proxy' in os.environ:
        proxy = os.environ['http_proxy']
        pip_args.append('--proxy')
        pip_args.append(proxy)
    
    pip_args.append('install')
    
    for req in REQUIREMENTS:
        pip_args.append( req )
    
    pip.main(initial_args = pip_args) 


def _make_package():
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    result = subprocess.check_output(["python", "setup.py", "bdist_wheel"], stderr = subprocess.STDOUT, universal_newlines=True)
    logging.debug(result)
    shutil.rmtree("build")

    #todo: test package
    #pushd functional_tests > /dev/null
    #./package_tests.sh


def _publish():
    result = subprocess.check_output(["python", "setup.py", "bdist_wheel", "upload"], stderr=subprocess.STDOUT, universal_newlines=True)
    logging.debug(result)

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
    logging.debug("Creating code analysis log file " + stats_log_filename)
    stats_log = open(stats_log_filename, "w")

    for (folder, subfolders, files) in os.walk(pyjen_path):
        for cur_file in files:
            cur_file_full_path = os.path.join(folder, cur_file)
            result = subprocess.check_output(["radon", "cc", "-sa", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            logging.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)
            result = subprocess.check_output(["radon", "raw", "-s", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            logging.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)
            result = subprocess.check_output(["radon", "mi", "-s", cur_file_full_path], stderr=subprocess.STDOUT, universal_newlines=True)
            logging.log(VERBOSE_LOGGING_LEVEL, result)
            stats_log.write(result)

    stats_log.close()
    
def _run_tests():
    # todo: run unit tests
    #py.test --cov-report term-missing --cov pyjen -s ./unit_tests/test*.py --verbose --junit-xml test_results.xml > "$log_folder/pytest.log" 2>&1
    params = ["py.test", "--cov-report", "term-missing", "--cov pyjen", "-s", r".\unit_tests", "--verbose", "--junit-xml", "test_results.xml"]
    result = subprocess.check_output(params, stderr=subprocess.STDOUT, universal_newlines=True)
    logging.log(VERBOSE_LOGGING_LEVEL, result)
    # todo see if we are asked to run functional tests and run them
    #py.test --cov-report term-missing --cov pyjen -s ./functional_tests/*tests.py --verbose --junit-xml test_results.xml > "$log_folder/func_pytest.log" 2>&1
    pass


def _configure_logger():
    log_file = os.path.join(log_folder, "run.log")

    file_log_format = "%(asctime)s %(levelname)s:%(message)s"
    logging.basicConfig(filename=log_file, filemode='w', format=file_log_format, level=logging.DEBUG)
    
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    
    console_log_format = "%(asctime)s: %(message)s"
    console_formatter = logging.Formatter(console_log_format)
    console_formatter.datefmt = "%H:%M"
    console_logger.setFormatter(console_formatter)

    logger = logging.getLogger()
    logger.addHandler(console_logger)

    
def _get_args():
    _parser = argparse.ArgumentParser( description='PyJen configuration utility')
    
    _parser.add_argument('--prep_env', action='store_true', help='Installs all Python packages used by PyJen sources')
    _parser.add_argument('--package', action='store_true', help='Generates redistributable package for PyJen')
    _parser.add_argument('--stats', action='store_true', help='Run static code analysis again PyJen sources')
    _parser.add_argument('--publish', action='store_true', help='Publish release artifacts online to PyPI')
    _parser.add_argument('--unittest', action='store_true', help='Runs unit test suite for the project')
    #_parser.add_argument('--functest', action='store_true', help='Runs functional test suite for the project')

    if len (sys.argv) == 1:
        _parser.print_help()
        sys.exit(1)
        
    _args = _parser.parse_args()
    logging.debug("Command line params: " + str(_args))
    
    return _args


if __name__ == "__main__":
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    _configure_logger()
    
    args = _get_args()

    if args.prep_env:
        logging.info('installing dependencies...')
        _prepare_env()
        logging.info("dependencies installed successfully")
        
    if args.package:
        logging.info("creating package...")
        _make_package()
        logging.info("package created successfully")

    if args.stats:
        logging.info("Running code analysis tools...")
        _code_analysis()
        logging.info("Code analysis complete")

    if args.publish:
        logging.info("publishing release...")
        _publish()
        logging.info("release published successfully")

    if args.unittest:
        logging.info("running unit tests...")
        _run_tests()
        logging.info("finished running tests")