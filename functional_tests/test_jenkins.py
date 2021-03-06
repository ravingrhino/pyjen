import pytest
from functional_tests.test_utils import JenkinsProcess, safe_delete
from pyjen.jenkins import Jenkins
import os
import unittest
import tempfile
import shutil


def setup_workspace(config_folder):
    """Helper function used to prepare a test workspace for Jenkins
    
    The sample configuration stored in the specified folder will be cloned
    to a temporary location for use by the tests
    
    :param str config_folder: the name of the configruation folder containing the sample files for Jenkins' config
    :return: The path of the newly created temporary Jenkins "home" folder
    :rtype: `func`:str
    """
    
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_folder)
    
    tmp_dir = tempfile.mkdtemp(prefix="pyjen_test")
    target_dir = os.path.join(tmp_dir, config_folder)
    
    shutil.copytree(src_path, target_dir)
    return target_dir


class lts_tests(unittest.TestCase):
    """Functional tests applied to the LTS edition of Jenkins"""
    @classmethod
    def get_edition(cls):
        return "lts"
    
    @classmethod
    def setUpClass(cls):
        cls._jenkins_home = setup_workspace("jenkins_job_view")
        cls._jenkins = JenkinsProcess(cls.get_edition())
        cls._jenkins.start(cls._jenkins_home)
        cls._jenkins_url = cls._jenkins.url
        
    @classmethod
    def tearDownClass(cls):
        print("killing jenkins")
        cls._jenkins.terminate()
        # todo: see if this call should be moved into terminate()
        #(sout, serr) = self._jenkins_process.communicate()
        #print ("done killing: " + str(sout) + " - " + str(serr))

        #clean up working folder
        safe_delete(os.path.abspath(os.path.join(cls._jenkins_home, "..")))

    def test_create_view(self):
        new_view_name = "test_create_view"
        j = Jenkins.easy_connect(self._jenkins_url, None)
        j.create_view(new_view_name, "hudson.model.ListView")
        v = j.find_view(new_view_name)
        
        self.assertTrue(v is not None)
        
        self.assertEqual(v.name, new_view_name)
        
    def test_shutdown(self):
        j = Jenkins.easy_connect(self._jenkins_url, None)

        self.assertFalse(j.is_shutting_down)
        j.prepare_shutdown()
        self.assertTrue(j.is_shutting_down)
        
        j.cancel_shutdown()
        self.assertFalse(j.is_shutting_down)

    def test_default_view(self):
        j = Jenkins.easy_connect(self._jenkins_url, None)
        
        v = j.default_view
        self.assertIsNotNone(v)
        self.assertEqual("All", v.name)        
        
    def test_find_view(self):
        expected_view_name = "ViewNumber1"
        
        j = Jenkins.easy_connect(self._jenkins_url, None)
        
        v = j.find_view(expected_view_name)
        
        self.assertEqual(expected_view_name, v.name)
        
    def test_find_job(self):
        expected_job_name = "JobNumber1"
        
        j = Jenkins.easy_connect(self._jenkins_url, None)
        
        job = j.find_job(expected_job_name)
        
        self.assertEqual(expected_job_name, job.name)
        
    def test_last_build(self):
        job_url = self._jenkins_url + "/job/JobNumber1"

        j = Jenkins.easy_connect(self._jenkins_url, None)

        job = j.get_job(job_url)

        #sanity check: make sure our generated URL works correctly
        self.assertEqual("JobNumber1", job.name)
        
        build = job.last_build
        
        self.assertEqual(2, build.number)
        
    def test_last_good_build(self):
        job_url = self._jenkins_url + "/job/JobNumber1"

        j = Jenkins.easy_connect(self._jenkins_url, None)

        job = j.get_job(job_url)

        #sanity check: make sure our generated URL works correctly
        self.assertEqual("JobNumber1", job.name)
        
        build = job.last_good_build
        
        self.assertEqual(1, build.number)
        self.assertEqual("SUCCESS", build.result)
        
    def test_last_failed_build(self):
        job_url = self._jenkins_url + "/job/JobNumber1"

        j = Jenkins.easy_connect(self._jenkins_url, None)

        job = j.get_job(job_url)

        #sanity check: make sure our generated URL works correctly
        self.assertEqual("JobNumber1", job.name)
        
        build = job.last_failed_build
        
        self.assertEqual(2, build.number)
        self.assertEqual("FAILURE", build.result)

    def test_get_builds(self):
        job_url = self._jenkins_url + "/job/JobNumber1"

        j = Jenkins.easy_connect(self._jenkins_url, None)

        job = j.get_job(job_url)

        #sanity check: make sure our generated URL works correctly
        self.assertEqual("JobNumber1", job.name)
        
        builds = job.recent_builds
        
        self.assertEqual(2, len(builds))
        expected_numbers = [1, 2]
        expected_results = ["SUCCESS", "FAILURE"]
        for build in builds:
            self.assertTrue(build.number in expected_numbers)
            self.assertTrue(build.result in expected_results)
            expected_numbers.remove(build.number)
            expected_results.remove(build.result)


class latest_tests(lts_tests):
    """Repetition of all LTS functional tests in the latest Jenkins version"""
    @classmethod
    def get_edition(self):
        return "latest"
    
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
