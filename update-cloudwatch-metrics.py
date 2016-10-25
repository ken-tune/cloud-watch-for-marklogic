import boto
from boto.ec2.cloudwatch import CloudWatchConnection
from boto.ec2.cloudwatch.alarm import MetricAlarm

import requests
from requests.auth import HTTPDigestAuth

import xml.etree.ElementTree
import re

import optparse

parser = optparse.OptionParser()
parser.set_defaults(debug=False)
parser.set_defaults(setAlarm=False)
parser.add_option('--debug',action="store_true",dest='debug')
parser.add_option('--storeMetrics',action="store_true",dest='storeMetrics')
parser.add_option('--setAlarm',action="store_true",dest='setAlarm')
parser.add_option('--deleteAlarm',action="store_true",dest='deleteAlarm')
(options, args) = parser.parse_args()

# Constants
CURRENT_VALUE_INSTRUCTION = "#CURRENT_VALUE#"
DEFAULT_GROUP="Default"
SERVER_TYPE="Servers"
CONFIG_NE_OPERATOR="ne"
CONFIG_GT_OPERATOR="gt"
CONFIG_LT_OPERATOR="lt"
AWS_LT_OPERATOR="<"
AWS_GT_OPERATOR=">"

# Application specific configuration
import config
USER=config.USER
PASSWORD=config.PASSWORD
HOST=config.HOST
SERVER_NAME=config.SERVER_NAME
SNS_TOPIC=config.SNS_TOPIC

if hasattr(config,"SERVER_DATABASE"):
    SERVER_DATABASE=config.SERVER_DATABASE
else:
    SERVER_DATABASE=SERVER_NAME+"-content"

# Cloud Watch Connection object
cwc = CloudWatchConnection()

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

def urlPrefix():
	return "http://"+HOST+":8002"

def is_numeric(_string):
	return _string.replace('.','',1).isdigit()	

def get_json(url):
	return requests.get(url, auth=HTTPDigestAuth(USER,PASSWORD)).json()

def get_hosts():
	url = urlPrefix() + "/manage/v2/hosts?format=json"
	hosts = {}
	for item in get_json(url)["host-default-list"]["list-items"]["list-item"]:
		hosts[item["idref"]] = item["nameref"]
	return hosts

def get_clusters():
	url=urlPrefix() + "/manage/v2/clusters?cluster-role=foreign&format=json"
	clusters = {}
	cluster_data = get_json(url)["cluster-default-list"]["list-items"]
	if "list-item" in cluster_data:
		for item in cluster_data["list-item"]:
			clusters[item["idref"]] = item["nameref"]
	return clusters

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

def processValue(value,op):
	if op == None:
		return value
	else:
		parts = op.split("=")
		if(parts[0] == "eq"):
			if parts[1] == value:
				return 1
			else:
				return 0
		elif(parts[0] == "ne"):
			if parts[1] != value:
				return 1
			else:
				return 0
		else:
			return 0

def process_item(item,metricName,op,thresholds):
	if(op != None):
		unit = "None"
	else:
		unit = unitTranslation[str(item["units"])]	

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
	value = processValue(value,op)
	if isinstance(value,int) or is_numeric(value):
		if options.storeMetrics:
			print "Inserting name:"+metricName+" unit:"+unit+" value:"+str(value)
			if not options.debug:			
				cwc.put_metric_data(namespace=SERVER_NAME,name=metricName,unit=unit,value=value)			
		if options.setAlarm:
			if thresholds is not None:
				for threshold in thresholds.iter("threshold"):
					thresholdType = threshold.find("type").text
					thresholdOperator = threshold.find("comparison-operator").text
					thresholdValue = threshold.find("value").text
					if thresholdValue == CURRENT_VALUE_INSTRUCTION:
						thresholdValue = value
					if thresholdOperator == CONFIG_NE_OPERATOR:
						set_alarm(name=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_GT_OPERATOR)
						set_alarm(name=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_LT_OPERATOR)						
					elif thresholdOperator == CONFIG_GT_OPERATOR:
						set_alarm(name=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_GT_OPERATOR)
					elif thresholdOperator == CONFIG_LT_OPERATOR:
						set_alarm(name=metricName,thresholdValue=thresholdValue,unit=unit,thresholds=thresholds,operator=AWS_LT_OPERATOR)						
		if options.deleteAlaram
					if thresholdOperator == CONFIG_NE_OPERATOR:
						delete_alarm(name=metricName)
						delete_alarm(name=metricName)						
					elif thresholdOperator == CONFIG_GT_OPERATOR:
						delete_alarm(name=metricName)
					elif thresholdOperator == CONFIG_LT_OPERATOR:
						delete_alarm(name=metricName)

	else:
		print "Not numeric :"+metricName+" unit:"+unit+" value:"+str(value)

def get_data(path,desc,key,id,idName,op,thresholds):
	path = re.sub("\$_HOSTMLALIAS\$",str(id),path)
	key = re.sub("\$SERVICEDESC\$",desc,key)

	url = urlPrefix() +path
	if "?" in url:
		url = url + "&format=json"
	else:
		url = url + "?format=json"		
	if _type == SERVER_TYPE:
		url  = url + "&group-id="+DEFAULT_GROUP
	json =  get_json(url)
	metricName = desc
	for item in gen_dict_extract(key,json):
		if isinstance(item,dict):
			if 'value' in item:
				if idName:
					metricName = metricName + " : " +idName
				process_item(item,metricName,op,thresholds)
			else:			
				for desc in item:
					sub_item= item[desc]
					process_item(sub_item,desc,op,thresholds)
                else:
                    process_item({"value":item,"unit":"Count"},desc,op)

	if len(list(gen_dict_extract(key,json))) ==0:
			print "XXX - " + key + " not found"				

def set_alarm(name,thresholdValue,unit,thresholds,operator):	
	print "put-metric-alarm(alarm-name="+name+ \
	",alarm-description="+name+\
	",metric-name="+name+\
	",namespace="+SERVER_NAME+\
	",statistic=Average"+\
	",period=120"+\
	"threshold="+thresholdValue+\
	"comparison-operator="+operator+\
	",evaluation-periods=1"+\
	",alarm-actions="+config.SNS_TOPIC+\
	",unit="+unit
	if not options.debug:
		cwc.put_metric_alarm(MetricAlarm(
			name=name,
			description=name,
			alarm_actions=config.SNS_TOPIC,
			metric=name,
			namespace=SERVER_NAME,
			statistic="Average",
			period=120,
			unit=unit,
			evaluation_periods=1,
			threshold=thresholdValue,
			comparison=operator
		))

def delete_alarm(alarmName):
	print "Deleting alarm "+alarmName
	if not options.debug:
		cwc.delete_alarms(alarmName)

e = xml.etree.ElementTree.parse('metrics.xml').getroot()

_hash = {"localcluster":1,"clusters":get_clusters(),"hosts":get_hosts(),"databases":SERVER_DATABASE,"servers":SERVER_NAME}

for metric in e.findall('metric'):
	_type = metric.get("type")
	_ids = _hash[_type.lower()]
	_path = metric.find("path").text
	_key = metric.find("key").text
	_desc = metric.find("service_description").text
	thresholds = metric.find("thresholds")

	_op = None
	if metric.find("op") != None:
		_op  = metric.find("op").text

	if isinstance(_ids,dict):
		for _id in _ids:
			get_data(_path,_desc,_key,_id,_ids[_id],_op,thresholds)
	else:
		get_data(_path,_desc,_key,_ids,None,_op,thresholds)
	
