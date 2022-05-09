#!/bin/bash
#This script is run at container initialisation to start locust

#define the location of the locust programme in the container
locust_programme="/usr/local/bin/locust"

#receive the locust mode from the environment variable locust_node_type
locust_node_type=${LOCUST_MODE:-standalone}
#locust_node_type=${locust_is_master:-standalone}

#if the locust_node_type is "master"
if [[ "$locust_node_type" = "master" ]]; then
    #set the bash command to set the node to master with the --master flag
    locust_command="-f ./locust/locustfile.py --host=$TARGET_HOST --csv=$TEST_NAME --master --expect-workers=5"

#if the locust_node_type is "worker"
elif [[ "$locust_node_type" = "worker" ]]; then
    #set the bash command to set the node to worker with the --worker flag
    locust_command="-f ./locust/locustfile.py --host=$TARGET_HOST --csv=$TEST_NAME --worker --master-port=5557 --master-host=$LOCUST_MASTER_NODE_HOST"
fi

#echo commands to the terminal
echo "$locust_programme $locust_command"
#run commands in terminal
$locust_programme $locust_command
