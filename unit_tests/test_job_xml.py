from unit_tests.xml_test_base import xml_test_case
from pyjen.utils.jobxml import JobXML
import pytest
from pyjen.plugins.subversion import Subversion
import sys

class job_xml_basic_config_tests(xml_test_case):
    """Tests for the JobXML class that use a trivial job configuration as input"""
    def setUp(self):
        self.__test_config = """
        <project>
          <actions/>
          <description/>
          <keepDependencies>false</keepDependencies>
          <properties/>
          <scm class="hudson.scm.NullSCM"/>
          <canRoam>true</canRoam>
          <disabled>false</disabled>
          <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
          <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
          <triggers class="vector"/>
          <concurrentBuild>false</concurrentBuild>
          <builders/>
          <publishers/>
          <buildWrappers/>
        </project>
        """

    def test_no_op(self):
        
        j = JobXML(self.__test_config)
        actual_xml = j.XML
        
        self.assertEqualXML(self.__test_config, actual_xml)
    def test_get_xml_return_type(self):
        j = JobXML(self.__test_config)
        actual_xml = j.XML

        # In python2 unicode strings are of type 'unicode'
        # but in python3 'unicode' was deprecated because all strings are unicode
        if sys.version_info[0] < 3:
            self.assertEqual(type(actual_xml), unicode)
        else:        
            self.assertEqual(type(actual_xml), str)
    
    def test_new_custom_workspace(self):    
        custom_workspace_path = "something/else"
        
        j = JobXML(self.__test_config)
        j.custom_workspace = custom_workspace_path
        actual_xml = j.XML
        
        self.assertTrue("<customWorkspace>" + custom_workspace_path + "</customWorkspace>" in actual_xml)
        
    def test_disable_empty_custom_workspace(self):
        # our sample config does not have a custom workspace
        j = JobXML(self.__test_config)
        # make sure disabling custom workspace when none exists doesn't fail
        j.disable_custom_workspace()
        
        actual_xml = j.XML
        
        self.assertTrue("<customWorkspace>" not in actual_xml)
        
    def test_change_custom_workspace(self):
        sample_xml = """
        <project>
          <actions/>
          <description/>
          <keepDependencies>false</keepDependencies>
          <properties/>
          <scm class="hudson.scm.NullSCM"/>
          <canRoam>true</canRoam>
          <disabled>false</disabled>
          <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
          <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
          <triggers class="vector"/>
          <concurrentBuild>false</concurrentBuild>
          <customWorkspace>my/test/workspace</customWorkspace>
          <builders/>
          <publishers/>
          <buildWrappers/>
        </project>"""
        
        new_custom_workspace = "some/new/path"
        j = JobXML(sample_xml)
        j.custom_workspace = new_custom_workspace
        actual_xml = j.XML
        
        self.assertTrue("<customWorkspace>" + new_custom_workspace + "</customWorkspace>" in actual_xml)
        
    def test_disable_custom_workspace(self):
        sample_xml = """
        <project>
          <actions/>
          <description/>
          <keepDependencies>false</keepDependencies>
          <properties/>
          <scm class="hudson.scm.NullSCM"/>
          <canRoam>true</canRoam>
          <disabled>false</disabled>
          <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
          <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
          <triggers class="vector"/>
          <concurrentBuild>false</concurrentBuild>
          <customWorkspace>my/test/workspace</customWorkspace>
          <builders/>
          <publishers/>
          <buildWrappers/>
        </project>"""
        
        j = JobXML(sample_xml)
        j.disable_custom_workspace()
        actual_xml = j.XML
        
        self.assertTrue("<customWorkspace>" not in actual_xml)
    
    def test_get_svn_scm(self):
        sample_xml = """
        <project>
            <scm class="hudson.scm.SubversionSCM" plugin="Subversion@1.53">
                <locations>
                    <hudson.scm.SubversionSCM_-ModuleLocation>
                        <remote>http://repository/project/trunk</remote>
                        <local>.</local>
                        <depthOption>infinity</depthOption>
                        <ignoreExternalsOption>false</ignoreExternalsOption>
                    </hudson.scm.SubversionSCM_-ModuleLocation>
                </locations>
                <excludedRegions/>
                <includedRegions/>
                <excludedUsers/>
                <excludedRevprop/>
                <excludedCommitMessages/>
                <workspaceUpdater class="hudson.scm.Subversion.UpdateUpdater"/>
                <ignoreDirPropChanges>false</ignoreDirPropChanges>
                <filterChangelog>false</filterChangelog>
            </scm>
        </project>"""
        
        j = JobXML(sample_xml)
        scm = j.scm
        #print(dir(scm.__class__))
        #print(dir(Subversion))
        #print(scm.__class__.__module__)
        #print(Subversion.__class__.__module__)
        #self.assertEqual(scm.__class__, Subversion)

        # TODO: Figure out why this doesn't work
        #self.assertIsInstance(scm, abc)

        self.assertEqual(scm.type, Subversion.type)

if __name__ == '__main__':
    pytest.main([__file__, "-v", "-s"])
