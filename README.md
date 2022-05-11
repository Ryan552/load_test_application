# CloudProphecy - load_test_application

CloudProphecy - A user-centric cloud benchmarking and monitoring tool for data visualisation and cloud VM recommendations

## Introduction

Locust is a Python based load testing library. It can be used to apply load on a web server by simulating multiple concurrent users making specified http requests as per a configurable user definition. Locust can be ran in a distributed manner, allowing the load of the locust process to be shared over multiple CPU cores.
This repository is for a containerised application that deploys Locust in a distributed manner. A Locust master node and 5 worker nodes are deployed on Google Cloud Platform's Kubernetes Engine.

## Deployment

The following services should be enabled in your project before deployment:
Cloud Build
Kubernetes Engine
Cloud Storage

This application is to be deployed on google kubernetes after the Banchmark_Application and results-server has been set up.

Open a Google Cloud Shell Terminal to run the run_script.sh shell script, modifying the following variables to suit the benchmark being conducted:

 - $projectID="rglynn01-40127817"
 - $zone=us-central1-b
 - $clusterName=load_test_application
 - $targetIP="34.88.122.184:8080"
 - $APP_NAME=example_app
 - $VM_NAME=example_VM
 - $resultServerIP="34.71.167.147"

The output of the run_script.sh script prints the external IP address of the locust UI.

Open the IP address, access the locust UI.

Check that the target IP address on the UI matches the benchmark application, this is the last chance to change this.

Start the Locust Load test on the UI.

As default the load shape will modify the user count to aim to maintain the response time between thresholds:
  -	Median response time threshold: 		1000 ms
  -	95th Percentile response time threshold:    3000 ms

This is controlled in the file docker-image/locust/locustfile.py.
The user definition is also controlled in the locustfile.py.
For more information on locust library please read the documentation:
https://docs.locust.io/en/stable/

## Termination

To stop the benchmark, stop the test in the locust UI and run the stop_script.sh script which will terminate and remove the kubernetes cluster.
