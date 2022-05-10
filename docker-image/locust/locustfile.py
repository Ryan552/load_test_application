#Import required libraries
import time
import atexit
import locust
import logging
import gevent
import socket
from locust import FastHttpUser, task, between, constant, LoadTestShape, events
from locust.runners import STATE_INIT, STATE_RUNNING, STATE_SPAWNING, STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP, MasterRunner, LocalRunner, WorkerRunner

#Initialising the global control variables that will be used to control the dynamic load test
#threshold_ratio --> ratio of response time to response time thresholds
#first_fully_loaded --> boolean to indicate if VM has yet reached a fully loaded state
#user_count --> current count of spawned users in locust
#run_time --> current benchmark run time in seconds
#threshold_median --> the threshold for median response time
#threshold_95perc --> the threshold for 95th percentile response time
threshold_ratio = 0
first_fully_loaded = False
user_count = 0
run_time = 0
threshold_median = 1000
threshold_95perc = 3000
records_start_time = 1651795200

#Function that checks the current state of the response time and sets the global control variables approporately
def check_load(environment):

    #initialise global variables inside function
    global threshold_ratio
    global first_fully_loaded

    #Run while the state of the locust master's run state is not stopping, stopped or in post stop cleanup
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:

        #add time delay reduce the rate that the response time is checked and control variables are updated
        time.sleep(1)

        #If the locust runner is reporting values for the response time, i.e. integers
        if isinstance(environment.runner.stats.total.get_current_response_time_percentile(0.5), int) :

            #receive the response time from the locust runner and set to variables
            response_time_median = environment.runner.stats.total.get_current_response_time_percentile(0.5)
            response_time_95perc = environment.runner.stats.total.get_current_response_time_percentile(0.95)

            #If both the median and 95 percentile are above their respective thresholds
            if response_time_median > 1000 and response_time_95perc > 3000 :

                print(f"reducing load on server, both thresholds breached", flush=True)
                #set threshold_ratio to the multiplication of the ratios of response time to the thresholds
                threshold_ratio = (response_time_median/1000)*(response_time_95perc/3000)
                #set to True to indicate VM has been fully loaded
                first_fully_loaded = True

            #Else if just the median is above the threshold,
            elif response_time_median > 1000:

                print(f"reducing load on server, median threshold breached", flush=True)
                #set threshold_ratio to the ratio of response time to the threshold
                threshold_ratio = response_time_median/1000
                #set to True to indicate VM has been fully loaded
                first_fully_loaded = True

            #Else if just the 95 percentile is above the threshold,
            elif response_time_95perc > 3000:

                print(f"reducing load on server, 95th percentile threshold breached", flush=True)
                #set threshold_ratio to the ratio of response time to the threshold
                threshold_ratio = response_time_95perc/3000
                #set to True to indicate VM has been fully loaded
                first_fully_loaded = True

            #Else if neither the median of 95 percentile are above the thresholds
            else :
                #set threshold_ratio to the ratio of response time to the threshold
                threshold_ratio = response_time_median/1000

#funtion to send regular reports of the metrics to Graphite via a socket connection
def send_report(environment):

    #initialise global variables inside function
    global user_count
    global run_time
    global records_start_time

    #create a socket connection and connect using the IP address of the Results Server
    sock = socket.socket()
    sock.connect( ("[RESULTS_IP]", 2003) )

    #Run while the state of the locust master's run state is not stopping, stopped or in post stop cleanup
    while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:

        #add time delay to reduce the rate that the reports are sent to Graphite to avoid unnecessary network traffic
        time.sleep(0.5)

        #if the locust load test is running
        if environment.runner.state == STATE_RUNNING or environment.runner.state == STATE_SPAWNING:

            #checks for Nulls and assigns the median response time
            if environment.runner.stats.total.get_current_response_time_percentile(0.5) is None:
                response_time_median = 0
            else:
                response_time_median = environment.runner.stats.total.get_current_response_time_percentile(0.5)

            #checks for Nulls and assigns the median response time
            if environment.runner.stats.total.get_current_response_time_percentile(0.95) is None:
                response_time_95perc = 0
            else:
                response_time_95perc = environment.runner.stats.total.get_current_response_time_percentile(0.95)

            #checks if the num_reqs_per_sec dictionary in locust has a value for the current time with a 3 second delay to allow the dict to be written
            if round(time.time()-3) in environment.runner.stats.total.num_reqs_per_sec:
                #assigns the requests_per_second from 3 seconds ago
                requests_per_second = environment.runner.stats.total.num_reqs_per_sec[round(time.time()-3)]
            else :
                print("no requests per second recorded for this timeframe")
                requests_per_second = 0

            #checks if the num_fail_per_sec dictionary in locust has a value for the current time with a 3 second delay to allow the dict to be written
            if round(time.time()-3) in environment.runner.stats.total.num_fail_per_sec:
                #assigns the failures_per_second from 3 seconds ago
                failures_per_second = environment.runner.stats.total.num_fail_per_sec[round(time.time()-3)]
            else :
                print("no failures per second recorded for this timeframe")
                failures_per_second = 0

            #benchmark_time is the time that will be sent to Graphite
            benchmark_time = round(run_time) + records_start_time
            #benchmark_time_delayed is a 3 second delayed time for recording the requests per second and failures per second in Graphite
            benchmark_time_delayed = benchmark_time - 3

            #messages in Graphite's Plaintext protocol to be sent to Graphite through socket
            #[APP_NAME] and [VM_NAME] are distinctly named so that they can be edited by the run_script.sh bash script for starting the benchmark application
            response_time_median_message = "%s %d %d\n" % ("benchmarking.locust.[APP_NAME].[VM_NAME].response_time.median", response_time_median, benchmark_time)
            response_time_95perc_message = "%s %d %d\n" % ("benchmarking.locust.[APP_NAME].[VM_NAME].response_time.95perc", response_time_95perc, benchmark_time)
            user_count_message = "%s %d %d\n" % ("benchmarking.locust.[APP_NAME].[VM_NAME].user_count", user_count, benchmark_time)
            requests_per_second_message = "%s %d %d\n" % ("benchmarking.locust.[APP_NAME].[VM_NAME].requests_per_second", requests_per_second, benchmark_time_delayed)
            failures_per_second_message = "%s %d %d\n" % ("benchmarking.locust.[APP_NAME].[VM_NAME].failures_per_second", failures_per_second, benchmark_time_delayed)

            #try, except for each of the metrics to catch any issues if a metric fails to send and avoid the code terminating from errors if one fails to send
            try:
                #send median response time message to Graphite
                sock.sendall(response_time_median_message.encode())
                print("median response time data has been sent to graphite: " + response_time_median_message, flush=True)
            except:
                print("issues sending median response time data to graphite", flush=True)

            try:
                #send 95th percentile response time message to Graphite
                sock.sendall(response_time_95perc_message.encode())
                print("95 percentile response time data has been sent to graphite: " + response_time_95perc_message, flush=True)
            except:
                print("issues sending 95 percentile response time data to graphite", flush=True)

            try:
                #send user count message to Graphite
                sock.sendall(user_count_message.encode())
                print("user count data has been sent to graphite: " + user_count_message, flush=True)
            except:
                print("issues sending user count data to graphite", flush=True)

            try:
                #send requests per second message to Graphite
                sock.sendall(requests_per_second_message.encode())
                print("requests per second data has been sent to graphite: " + requests_per_second_message, flush=True)
            except:
                print("issues sending requests per second data to graphite", flush=True)

            try:
                #send failures per second message to Graphite
                sock.sendall(failures_per_second_message.encode())
                print("failures per second data has been sent to graphite: " + failures_per_second_message, flush=True)
            except:
                print("issues sending failures per second data to graphite", flush=True)

    #shutdown and close socket resources once benchmark test has been stopped
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()

#locust listener that runs on init
@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    #Gevents that run on the master locust runner which runs the check_load and send_report functions
    if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, LocalRunner):
        gevent.spawn(check_load, environment)
        gevent.spawn(send_report, environment)

#Custom shape class that includes an algorithm that controls the users that are spawned by locust to maintain the response time at the thresholds after the initial spike load
class dynamicLoadShape(LoadTestShape):

    #initialise global variables inside class
    global first_fully_loaded
    global threshold_ratio
    global user_count
    global run_time

    #set limit variables for controlling the load test
    #time_limit --> limit on the maximum duration of the load test
    #max_users --> limit on the maximum users that can be spawned
    time_limit = 6000
    max_users = 10000

    #Locust calls the tick() method approximately once per second
    #the tick method outputs a tuple of the desired user count and spawn rate
    def tick(self):

        #initialise global variables inside function
        global first_fully_loaded
        global threshold_ratio
        global user_count
        global run_time

        #set global run_time with current run time
        #set global user_count with current user count
        run_time = self.get_run_time()
        user_count = self.get_current_user_count()

        #if run time is less than time limit
        if run_time < self.time_limit:
            #if user count is less than the maximum user count limit
            if user_count < self.max_users :
                #if the the VM hasn't yet breached a response time threshold, scale up users quickly
                if first_fully_loaded == False :

                    next_step = user_count + 20
                    return (next_step, 10)

                #if the the VM has breached a response time threshold modulate user count to find maximum
                elif first_fully_loaded == True :
                    #if threshold_ratio is greater than zero scale back the user count
                    if threshold_ratio > 1 :

                        #proposed_step is the reduction step in user count based off the threshold ratio
                        proposed_step = user_count - round(2*threshold_ratio)
                        #maximum_step sets a maximum step change in user count of -4% or -2 from the current user count
                        maximum_step = min(round(user_count*0.96),user_count-2)
                        #next_step is calculated as the max of the proposed_step, maximum_step and 1
                        next_step = max(max(proposed_step,maximum_step),1)
                        #rate is calculated as the minimum of the threshold ratio or half the change in user count with a minimum value of 1.
                        rate = max(min(round(abs(threshold_ratio)), abs((maximum_step-user_count)/2)), 1)
                        #return tuple of next_step and rate
                        return (next_step, rate)

                    #if threshold_ratio is greater than zero scale back the user count
                    elif threshold_ratio < 1 :

                        #proposed_step is the increase step in user count based off the threshold ratio
                        proposed_step = user_count + round(2*threshold_ratio)
                        #maximum_step sets a maximum step change in user count of +4% or +2 from the current user count
                        maximum_step = max(round(user_count*1.04),user_count+2)
                        #next_step is calculated as the max of the proposed_step, maximum_step and 1
                        next_step = max(min(proposed_step,maximum_step),1)
                        #rate is calculated as the minimum of the threshold ratio or half the change in user count with a minimum value of 1.
                        rate = max(min(round(abs(threshold_ratio)), abs((maximum_step-user_count)/2)), 1)
                        #return tuple of next_step and rate
                        return (next_step, rate)

                    #else will cover when threshold_ratio = 1
                    else :
                        #return tuple of current user count as response time matches the threshold
                        return (user_count, 1)

            #else, for when the current user count is above the maximum
            else :
                #return user count below maximum allowed
                return (self.max_users-1, 10)

        #return none if time limit is reached
        return None

#Class defining the user definition for the http requests
class UserDefinition(FastHttpUser):

    #the wait time between the user receiving a response and sending another request
    wait_time = constant(1)

    #basic user task definition for sending http get request with query string integers i1 and i2
    @task
    def userTask(self):
        response = self.client.get(f"/?i1=333&i2=444")
