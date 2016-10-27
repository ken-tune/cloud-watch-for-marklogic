# This script can be used to manage MarkLogic's use of CloudWatch
# It writes metrics to CloudWatch based on metrics.xml
# It can also be used to create alarms based on the content of metrics.xml
# Flags --setAlarm, --deleteAlarm, 
import boto
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.cloudwatch.alarm import MetricAlarm
from boto.sns import SNSConnection

import requests
from requests.auth import HTTPDigestAuth

# XML Parsing Library
import xml.etree.ElementTree

# Regex Library
import re

# Command line parsing
import optparse

# Application specific configuration
import config

# Constants
CONFIG_FILE="metrics.xml"
CURRENT_VALUE_INSTRUCTION = "#CURRENT_VALUE#"
DEFAULT_GROUP="Default"
SERVER_TYPE="Servers"
# Constants used in metrics.xml
CONFIG_EQ_OPERATOR="eq"
CONFIG_NE_OPERATOR="ne"
CONFIG_GT_OPERATOR="gt"
CONFIG_LT_OPERATOR="lt"
# Strings used for alarm specification
AWS_LT_OPERATOR="<"
AWS_GT_OPERATOR=">"
EMAIL_PROTOCOL="email"

# Translate our units into AWS units
unitTranslation = {
	"%":"Percent",
	"MB":"Megabytes",
	"MB/sec":"Megabytes/Second",
	"bool":"None",
	"enum":"None",
	"hits/sec":"Count/Second",
	"misses/sec":"Count/Second",
	"quantity":"Count",
	"quantity/sec":"Count/Second",
	"sec/sec":"Count/Second"
}

# Parse command line options
# Can storeMetrics / create alarms / remove alarms
# Debug will give textual output without performing actions
parser = optparse.OptionParser()
parser.set_defaults(debug=False)
parser.set_defaults(storeMetrics=False)
parser.set_defaults(deleteAlarm=False)
parser.set_defaults(setAlarm=False)
parser.add_option('--debug',action="store_true",dest='debug')
parser.add_option('--storeMetrics',action="store_true",dest='storeMetrics')
parser.add_option('--setAlarm',action="store_true",dest='setAlarm')
parser.add_option('--deleteAlarm',action="store_true",dest='deleteAlarm')
(options, args) = parser.parse_args()

# Utility function to check if string is numeric
def is_numeric(_string):
	return _string.replace('.','',1).isdigit()	

# Mgmt service location
def mgmtServiceLocation():
	return "http://"+config.HOST+":8002"

# Get JSON from given URL
def get_json(url):
	return requests.get(url, auth=HTTPDigestAuth(config.USER,config.PASSWORD)).json()

# Get hash relating host ids to host names from mgmt service
def get_hosts():
	url = mgmtServiceLocation() + "/manage/v2/hosts?format=json"
	hosts = {}
	for item in get_json(url)["host-default-list"]["list-items"]["list-item"]:
		hosts[item["idref"]] = item["nameref"]
	return hosts

# get hash relating cluster ids to cluster names from mgmt service
def get_clusters():
	url=mgmtServiceLocation() + "/manage/v2/clusters?cluster-role=foreign&format=json"
	clusters = {}
	cluster_data = get_json(url)["cluster-default-list"]["list-items"]
	if "list-item" in cluster_data:
		for item in cluster_data["list-item"]:
			clusters[item["idref"]] = item["nameref"]
	return clusters

# Recursively look for all keys of a given name in a dictionary, and return the key values
def gen_dict_extract(key, var):
    if hasattr(var,'iteritems'):
        for k, v in var.iteritems():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in gen_dict_extract(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in gen_dict_extract(key, d):
                        yield result

# Given a value and an 'operator', if an operator is present test the value using the operator and return a boolean
# If no operator is provided, return the value
# So if the operator  = 'eq=available' then if value is 'available' return true else false
def processValue(value,op):
	if op == None:
		return value
	else:
		parts = op.split("=")
		if(parts[0] == CONFIG_EQ_OPERATOR):
			if parts[1] == value:
				return 1
			else:
				return 0
		elif(parts[0] == CONFIG_NE_OPERATOR):
			if parts[1] != value:
				return 1
			else:
				return 0
		else:
			return 0

def process_item(item,metricName,op,thresholds):
	# Sort out units - AWS has it's own system
	if(op != None):
		unit = "None"
	else:
		unit = unitTranslation[str(item["units"])]	

	# Extraction of metric value and stringifying
	value=None
	if isinstance(item,str):
		value = item
	elif isinstance(item,dict):
		if isinstance(item["value"],bool):
			value=str(item["value"]).lower()
		else:
			value = str(item["value"])
	else:
		value=str(item)

	# If value requires transformation, transform ( see processValue for detail )
	value = processValue(value,op)
	# Metric should be a number by this point - boolean true is represented by 1
	if isinstance(value,int) or is_numeric(value):
		# Store metric if instructed to do so
		if options.storeMetrics:
			print "Inserting name:"+metricName+" unit:"+unit+" value:"+str(value)
			if not options.debug:			
				cwc.put_metric_data(namespace=config.SERVER_NAME,name=metricName,unit=unit,value=value)			
		# If setAlarm flag set
		if options.setAlarm:
			# Threshold should be non-null
			if thresholds is not None:
				for threshold in thresholds.iter("threshold"):
					# Get threshold type - s/b/ warning or critical
					thresholdType = threshold.find("type").text
					# Get threshold operator - eq/gt/lt
					thresholdOperator = threshold.find("comparison-operator").text
					# Value associated with the threshold
					thresholdValue = threshold.find("value").text
					# Append thresholdType to metric name to give us warning and critical
					alarmName = thresholdType + " : " + metricName
					# If config says condition on current value ( e.g. host count) do that 
					if thresholdValue == CURRENT_VALUE_INSTRUCTION:
						thresholdValue = value
					# If threshold is the NE operator need to set two alarms - one for above, one for below
					if thresholdOperator == CONFIG_NE_OPERATOR:
						set_alarm(alarmName=alarmName+"-hi",metricName=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_GT_OPERATOR)
						set_alarm(alarmName=alarmName+"-lo",metricName=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_LT_OPERATOR)						
					# Else just the one alarm						
					elif thresholdOperator == CONFIG_GT_OPERATOR:
						set_alarm(alarmName=alarmName,metricName=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_GT_OPERATOR)
					elif thresholdOperator == CONFIG_LT_OPERATOR:
						set_alarm(alarmName=alarmName,metricName=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_LT_OPERATOR)						
			else:
				print "*** No threshold found for metric :"+metricName+ " - cannot set alarm ***"
		# If deleteAlarm flag set				
		if options.deleteAlarm:
			if thresholds is not None:
				for threshold in thresholds.iter("threshold"):
					# Get threshold type - s/b/ warning or critical					
					thresholdType = threshold.find("type").text
					# Get threshold operator - eq/gt/lt					
					thresholdOperator = threshold.find("comparison-operator").text
					# Append thresholdType to metric name to give us warning and critical					
					alarmName = thresholdType + " : " + metricName
					# If threshold is the NE operator need to delete two alarms - one for above, one for below					
					if thresholdOperator == CONFIG_NE_OPERATOR:
						delete_alarm(alarmName=alarmName+"-hi")
						delete_alarm(alarmName=alarmName+"-lo")						
					# Else just the one alarm												
					elif thresholdOperator == CONFIG_GT_OPERATOR:
						delete_alarm(alarmName=alarmName)
					elif thresholdOperator == CONFIG_LT_OPERATOR:
						delete_alarm(alarmName=alarmName)
	# If value is not numeric, something is wrong
	else:
		print "*** Not numeric :"+metricName+" unit:"+unit+" value:"+str(value) + " ***"

def processMetric(path,metricName,key,id,idName,op,thresholds,objectType):
	# If an object id is required by the Mgmt REST API replace with given object id ( e.g. host id )
	path = re.sub("\$OBJECT_ID\$",str(id),path)
	# If the required key is the same as the service description, set the key to be the service description
	key = re.sub("\$SERVICE_DESCRIPTION\$",metricName,key)
	# URL for metric
	url = mgmtServiceLocation() +path
	# add format=json
	if "?" in url:
		url = url + "&format=json"
	else:
		url = url + "?format=json"		
	# group parameter required for server requests
	if objectType == SERVER_TYPE:
		url  = url + "&group-id="+DEFAULT_GROUP
	# Get JSON
	json =  get_json(url)
	# Look for key in JSON
	for item in gen_dict_extract(key,json):
		# Should refer to a JSON object
		if isinstance(item,dict):
			# If it's of the form {units:, value: } the process
			if 'value' in item:
				if idName:
					# If a idName has bee supplied, add that to the metric name
					# e.g. separate compressed tree cache rate metrics for each host
					metricName = metricName + " : " +idName
				process_item(item,metricName,op,thresholds)
			# If it's not of the form {units:, value: } then we iterate through each key/object pair until we get to {units:,value:} and process that
			else:			
				for itemKey in item:
					sub_item= item[itemKey]
					process_item(sub_item,itemKey,op,thresholds)
		# If not then item is a scalar - package in {unit:,value} form and process
		else:
			process_item({"value":item,"units":"Count"},metricName,op,thresholds)

	if len(list(gen_dict_extract(key,json))) ==0:
			print "*** - " + key + " not found - skipping this metric ***"				

# A wrapper for the the boto put_metric_alarm function
def set_alarm(alarmName,metricName,thresholdValue,unit,thresholds,operator):	
	print "put-metric-alarm(alarm-name="+alarmName+ \
	",alarm-description="+metricName+\
	",metric-name="+metricName+\
	",namespace="+config.SERVER_NAME+\
	",statistic=Average"+\
	",period=120"+\
	"threshold="+thresholdValue+\
	"comparison-operator="+operator+\
	",evaluation-periods=1"+\
	",alarm-actions="+config.SNS_TOPIC+\
	",unit="+unit
	if not options.debug:
		cwc.put_metric_alarm(MetricAlarm(
			name=alarmName,
			description=metricName,
			alarm_actions=config.SNS_TOPIC,
			metric=metricName,
			namespace=config.SERVER_NAME,
			statistic="Average",
			period=120,
			unit=unit,
			evaluation_periods=1,
			threshold=thresholdValue,
			comparison=operator
		))

# A wrapper for the the boto delete_alarm function
def delete_alarm(alarmName):
	print "Deleting alarm "+alarmName
	if not options.debug:
		cwc.delete_alarms(alarmName)


def sns_arn_for_topic(topicName)
	snsConn=SNSConnection()
	all_topics=snsConn.get_all_topics()["ListTopicsResponse"]["ListTopicsResult"]["Topics"]
	matchingTopics=[x for x in all_topics if x["TopicArn"].endswith(":"+topicName)]
	topicARN=None
	if(len(matchingTopics)):
    topicARN=matchingTopic=matchingTopics[0]["TopicArn"]
	return topicARN

def check_sns_topic_exists(topicName)
	snsConn=SNSConnection()
	sns_arn - sns_arn_for_topic(topicName)
	if(sns_arn == None):
		print "No SNS topic yet for "+topicName+" - creating"
    sns_arn=str(snsConn.create_topic(topicName)["CreateTopicResponse"]["CreateTopicResult"]["TopicArn"])
	else:
		print "SNS topic for "+topicName+" exists"		    	
	return sns_arn

def check_subscription_exists(topicName,email):
	snsConn=SNSConnection()	
	topicARN=check_sns_topic_exists(topicName)
	subscriptions=snsConn.get_all_subscriptions_by_topic(topicARN,None)["ListSubscriptionsByTopicResponse"]["ListSubscriptionsByTopicResult"]["Subscriptions"]
	matching_subscriptions=[x for x in subscriptions if(x["Protocol"]==EMAIL_PROTOCOL and x["Endpoint"]==email)]
	if(len(matching_subscriptions)):
    print email+" is subscribed to topic "+topicName+" already"
	else:
  	print "Subscribing "+EMAIL+" to topic "+topicName
   	snsConn.subscribe(topicARN,PROTOCOL,email)	

check_subscription_exists(config.SERVER_NAME,config.EMAIL_FOR_SNS)
quit()

# Cloud Watch Connection object
cwc = CloudWatchConnection()

# Parse the metrics file
e = xml.etree.ElementTree.parse(CONFIG_FILE).getroot()

# Store relevant MarkLogic object ids - may be multiple values in the case of hosts / clusters
marklogicObjectIDs = {"localcluster":1,"clusters":get_clusters(),"hosts":get_hosts(),"databases":config.SERVER_DATABASE,"servers":config.SERVER_NAME}

# For each metric in the metrics file
for metricConfig in e.findall('metric'):
	# Get type - expected to be one of LocalCluster/Clusters/Hosts/Databases/Servers
	marklogicMetricObjectType = metricConfig.get("type")
	# Used to deteermine which of the marklogicObjectIDs to use when requesting mgmt API data	
	objectIDs = marklogicObjectIDs[marklogicMetricObjectType.lower()]
	# URL to use for getting metric data
	urlForMetric = metricConfig.find("path").text
	# Descriptive text for metric
	metricDescription = metricConfig.find("service_description").text
	# JSON key for metric ( often same as metricDescription, but not always )
	metricKey = metricConfig.find("key").text
	# thresholds element used for configuring alarm
	thresholds = metricConfig.find("thresholds")
	# test to apply to metric value, if test found
	metricValueTest = None
	if metricConfig.find("op") != None:
		metricValueTest  = metricConfig.find("op").text
	# If metric applies to more than one object, iterate through those objects
	if isinstance(objectIDs,dict):
		for objectID in objectIDs:
			processMetric(urlForMetric,metricDescription,metricKey,objectID,objectIDs[objectID],metricValueTest,thresholds,marklogicMetricObjectType)
	else:
		processMetric(urlForMetric,metricDescription,metricKey,objectIDs,None,metricValueTest,thresholds,marklogicMetricObjectType)
	
