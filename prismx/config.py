from configupdater import ConfigUpdater
from atlassian import Jira


config = ConfigUpdater()
config.read('scout.conf')


def testjira(url,username,password):
	jira = Jira(
    url=url,
    username=username,
    password=password)
	jira.reindex()

def updatejira(url,username,password):
	config['jira']['url'].value = url
	config['jira']['username'].value = username
	config['jira']['password'].value = password
	config['jira']['enabled'].value = 'true'
	config.update_file()


def jiraconfig():
	response = {"url" :config['jira']['url'].value,
				"username": config['jira']['username'].value
				}
	return response