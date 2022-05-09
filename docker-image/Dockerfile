# A Python 3.8 base image is used as the base image for the container
FROM python:3.8

#set the conventional working directory inside the container
WORKDIR /usr/src/app

#Copy the locust directory into the container
COPY locust ./locust

#pip3 is used to install the required dependencies saved in the requirements.txt file
RUN pip3 install -r ./locust/requirements.txt

#Expose the ports required for locust
EXPOSE 5557 5558 8089

#set the run.sh script to executable
RUN chmod 755 ./locust/run.sh

#ENTRYPOINT to start the container with the run.sh script that makes the calls to setup locust
ENTRYPOINT ["./locust/run.sh"]
