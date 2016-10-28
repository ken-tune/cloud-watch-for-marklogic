# CloudWatch for MarkLogic

CloudWatch for MarkLogic helps set up AWS CloudWatch monitoring and alarms for MarkLogic Server

## Quick Start

The ideal setup would use the standard MarkLogic AMI, which is built on AWS Linux. Setting up your MarkLogic cluster on AWS either manually or using [AWS CloudFormation](https://aws.amazon.com/cloudformation/)  is described [here](https://developer.marklogic.com/products/aws)

On any host in your cluster

* *sudo yum -y install git*
* *git clone git@github.com:mustard57/cloud-watch-for-marklogic.git*
* *cd cloud-watch-for-marklogic*
* Modify your settings in *config.py* ( see below )
* *./cronCloudWatchUpdate.sh* ( adds metric storing as a cron job )
* *python update-cloudwatch-metrics.py* --setAlarm ( sets up alarms )

## config.py

This file holds the config required to retrieve monitoring data from MarkLogic, label appropriately in AWS and configure email based alerting. It ships as below

```
USER="admin"
PASSWORD="admin"
HOST="localhost"
SERVER_NAME="cloudwatch-demo-rest"
SERVER_DATABASE="cloudwatch-demo-content"
EMAIL_FOR_SNS="youremail@yourdomain.com"```

Configure as follows

**USER** - user id used to retrieve monitoring data from MarkLogic. Must have the *manage-user* role  
**PASSWORD** - password for the above user  
**HOST** - MarkLogic host that will be used to access server metrics. If running these scripts on a host in the cluster, *localhost* is fine  
**SERVER_NAME** - Name of the *application* server you would like to monitor  
**SERVER_DATABASE** - Name of the *database* you would like to monitor  
**EMAIL_FOR_SNS** - When setting alarms up, *update-cloudwatch-metrics.py* creates an [SNS topic](https://aws.amazon.com/sns/) with name *SERVER_NAME* and subscribes *this address* to it. So configure with the address you would like alerts sent to.  

## cloudwatch-demo

It's nice to know it works, so CloudWatch for MarkLogic ships with an application, **cloudwatch-demo** that allows you to easily simulate a running application.

### About cloudwatch-demo

cloudwatch-demo supplies two endpoints on port 8006 by default. *http://YOUR_HOST:8006/LATEST/resources/content*	called as a GET request will retrieve a randomly chosen number of documents ( 1 - 10 ) while the same resource called as a PUT will create 1 - 10 documents. The documents are 500 - 1000 words long (randomly chosen), with the words being chosen from the file found in */data/available-vocabulary.xml*. The database is initially seeded with 1000 such documents. Just to keep things exciting, the [MarkLogic caches](https://docs.marklogic.com/guide/concepts/clustering#id_84427) get cleared on average every 40 requests. All these constants configurable via */lib/constants.xqy".

### Installation

* *cd test-application*
* Edit *deploy/local.properties* setting user and password properties to a user/password combination that allows application setup
* *./doAll.sh* ( runs ml local bootstrap  / deploy modules / deploy content - see [Roxy](https://github.com/marklogic/roxy) for details)
* If running a cluster, run *./ml local create_application_replica_forests* which will replicate application forests ( and you will get replication related metrics )

### Simulation via JMeter

You can simulate activity via [JMeter](http://jmeter.apache.org/). Install JMeter and then open jmeter/simulation-for-cloudwatch.jmx. Click 'Cloudwatch ata simulation', left hand side and set your parameters as needed




Install instructions
====================

sudo yum -y install git

cd cloud-watch-for-marklogic/
database over-ride ( content )
# modify config.py

Python 2.7
Install twice
Delete alarm

