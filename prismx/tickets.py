from atlassian import Jira
from configupdater import ConfigUpdater

config = ConfigUpdater()
config.read('scout.conf')


def issue(board,title,description):
    url = config['jira']['url'].value
    username = config['jira']['username'].value
    password =config['jira']['password'].value
    
    jira = Jira(
    url=url,
    username=username,
    password=password)
    ticket = {
    'project': {'key': '%s' % board},
    'issuetype': {
        "name": "Task"
    },
    'summary': '%s' %title ,
    'description': '%s' % description,
    }

    newissue = jira.issue_create(fields=ticket)

    return newissue['key']