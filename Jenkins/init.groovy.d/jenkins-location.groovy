import jenkins.model.JenkinsLocationConfiguration

def location = JenkinsLocationConfiguration.get()
def jenkinsUrl = System.getenv("JENKINS_URL") ?: "http://localhost:18081/"

location.setUrl(jenkinsUrl)
location.save()
