"""Primitives for operating on Jenkins views of type 'StatusView'"""
from pyjen.view import View


class StatusView(View):
    """Interface to Jenkins views of type 'StatusView'"""
    type = "hudson.plugins.status__view.StatusView"

    def __init__(self, controller, jenkins_master):
        """
        :param controller:
            class capable of handling common HTTP IO requests sent by this
            object to the Jenkins REST API
        :type controller: :class:`~.utils.datarequester.DataRequester`
        :param jenkins_master:
            Reference to Jenkins object associated with the master instance managing
            this job
        :type jenkins_master: :class:`~.jenkins.Jenkins`
        """
        super(StatusView, self).__init__(controller, jenkins_master)


if __name__ == "__main__":  # pragma: no cover
    pass

