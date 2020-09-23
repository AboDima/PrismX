from atlassian import Jira
from configupdater import ConfigUpdater
import ScoutView


def jira(request):
    config = ConfigUpdater()
    config.read('scout.conf')
    enabled = config['jira']['enabled'].value
    return {
        'jira_enabled': enabled
    }


def loadaccounts(request):
    response = ScoutView.Accounts()
    return {
    'loadaccounts':response
    }