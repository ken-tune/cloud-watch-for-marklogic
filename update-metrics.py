import boto
from boto.ec2.cloudwatch import CloudWatchConnection

import requests
from requests.auth import HTTPDigestAuth

import xml.etree.ElementTree
import re

USER="admin"
PASSWORD="admin"
HOST=mfa.demo.marklogic.com
APPLICATION_NAME="wisdom"
APPLICATION_DATABASE=APPLICATION_NAME+"-content"

DEFAULT_GROUP="Default"
SERVER_TYPE="Servers"

cwc = CloudWatchConnection()

def get_hosts():
	url = 'http://'+HOST+':8002/manage/v2/hosts?format=json'
	hosts = {}
	for item in requests.get(url, auth=HTTPDigestAuth(USER,PASSWORD)).json()["host-default-list"]["list-items"]["list-item"]:
		hosts[item["idref"]] = item["nameref"]
	return hosts

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

def get_data(path,desc,key,id,idName):
	path = re.sub("\$_HOSTMLALIAS\$",str(id),path)
	key = re.sub("\$SERVICEDESC\$",desc,key)

	url = 'http://localhost:8002'+path
	if "?" in url:
		url = url + "&format=json"
	else:
		url = url + "?format=json"		
	if _type == SERVER_TYPE:
		url  = url + "&group-id="+DEFAULT_GROUP

	json =  requests.get(url, auth=HTTPDigestAuth(USER,PASSWORD)).json()

	metricName = desc

	for item in  gen_dict_extract(key,json):
		if 'value' in item:
			unit = str(item["units"])

			if idName:
				metricName = metricName + " : " +idName
			print "Inserting name:"+metricName+" unit:"+unit+" value:"+str(item["value"])
			cwc.put_metric_data(namespace=APPLICATION_NAME,name=metricName,unit=unit,value=str(item["value"]))			
			print ""
		else:			
			for desc in item:
				sub_item = item[desc]
				unit = str(sub_item["units"])
				print "Inserting name:"+metricName+" unit:"+unit+" value:"+str(sub_item["value"])
				cwc.put_metric_data(namespace=APPLICATION_NAME,name=metricName,unit=unit,value=str(item["value"]))							
				print ""

	if len(list(gen_dict_extract(key,json))) ==0:
			print "XXX - " + key + " not found"				


e = xml.etree.ElementTree.parse('metrics.xml').getroot()

_hash = {"clusters":"xxx","hosts":get_hosts(),"databases":APPLICATION_DATABASE,"servers":APPLICATION_NAME}

for metric in e.findall('metric'):
	_type = metric.get("type")
	_ids = _hash[_type.lower()]
	_path = metric.find("path").text
	_key = metric.find("key").text
	_desc = metric.find("service_description").text

	if isinstance(_ids,dict):
		for _id in _ids:
			get_data(_path,_desc,_key,_id,_ids[_id])
	else:			
		get_data(_path,_desc,_key,_ids,None)
	