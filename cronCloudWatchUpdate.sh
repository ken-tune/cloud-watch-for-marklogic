#!/bin/bash

TMP_CRON_FILE=./mycron

#write out current crontab
crontab -l > $TMP_CRON_FILE

UPDATE_SCRIPT=update-cloudwatch-metrics.py
RUN_DIR=`pwd`
UPDATE_SCRIPT_PATH=$RUN_DIR/$UPDATE_SCRIPT
#echo new cron into cron file
echo "* * * * *  cd $RUN_DIR ; python $UPDATE_SCRIPT_PATH" >> $TMP_CRON_FILE

#install new cron file
crontab -u $USER $TMP_CRON_FILE
rm $TMP_CRON_FILE
