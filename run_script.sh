#vars to be edited based on the deployment criteria and benchmark application specification and deployment
projectID="rglynn01-40127817"
zone=us-central1-b
clusterName=load_test_application
targetIP="34.88.122.184:8080"
appName=test
vmName=test

scope="https://www.googleapis.com/auth/cloud-platform"
testReference="load_test_${appName}_${vmName}"

#set project name
gcloud config set project $projectID

#set cluster zone
gcloud config set compute/zone ${zone}

#change to working directory
cd load_test_application

#change the tasks.py file with the appName and vmName variables to ensure data is recorded correctly
sed -i -e "s/\[APP_NAME\]/$appName/g" docker-image/locust/locustfile.py
sed -i -e "s/\[VM_NAME\]/$vmName/g" docker-image/locust/locustfile.py

#wait for background setup processes to finish before proceeding
wait

#create cluster, this may take several minutes
gcloud container clusters create $clusterName \
   --zone $zone \
   --scopes $scope \
   --num-nodes 7 \
   --scopes=logging-write,storage-ro \
   --addons HorizontalPodAutoscaling,HttpLoadBalancing #\
   #--enable-autoscaling --min-nodes 3 --max-nodes 10 \

#wait for cluster to be created
wait

#connect to cluster
gcloud container clusters get-credentials $clusterName \
   --zone $zone \
   --project $projectID

#wait for connection to cluster
wait

#build docker image for locust application
gcloud builds submit \
    --tag gcr.io/$projectID/load-test-application:latest docker-image

#wait for the docker image to be built
wait

#check the docker container is built correctly by printing to screen
gcloud container images list | grep load-test-application

#wait for docker image printout
wait

#change TARGET_HOST and PROJECT_ID to the $targetIP and $projectID environment variables
sed -i -e "s/\[PROJECT_ID\]/$projectID/g" k8-config/deployment-locust-master.yaml
sed -i -e "s/\[PROJECT_ID\]/$projectID/g" k8-config/deployment-locust-worker.yaml
sed -i -e "s/\[TARGET_HOST\]/$targetIP/g" k8-config/deployment-locust-master.yaml
sed -i -e "s/\[TARGET_HOST\]/$targetIP/g" k8-config/deployment-locust-worker.yaml
sed -i -e "s/\[TEST_NAME\]/$testReference/g" k8-config/deployment-locust-master.yaml
sed -i -e "s/\[TEST_NAME\]/$testReference/g" k8-config/deployment-locust-worker.yaml

#wait for the kubernetes-config files to be edited
wait

#deploy the master and workers nodes on the kubernetes cluster
kubectl apply -f k8-config/deployment-locust-master.yaml
kubectl apply -f k8-config/service-locust-master-.yaml
kubectl apply -f k8-config/deployment-locust-worker.yaml

#wait for the master node to be deployed on the cluster
wait

#verify the services have been set up
kubectl get services

echo "waiting for an external IP address to be assigned"

#set the $externalIP environment variable
externalIP=$(kubectl get svc locust-master -o jsonpath="{.status.loadBalancer.ingress[0].ip}")

#loop to check every second if the external IP address has been assigned
while [ -z $externalIP ]; do externalIP=$(kubectl get svc locust-master -o jsonpath="{.status.loadBalancer.ingress[0].ip}"); sleep 1; done

echo "The external IP for the master has been assigned as: $externalIP"
echo "Open the IP Address: http://$externalIP:8089 on your browser to see the locust hmi"
echo "you may have to wait for the worker nodes to finish deployment and connect to the master node"
