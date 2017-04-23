__author__ = 'tkraus'

import sys
import requests
import json
import math

class marathon(object):
    def __init__(self, dcos_master,dcos_auth_token):
        self.name = dcos_master
        self.uri=(dcos_master)
        self.headers={'Authorization': 'token='+dcos_auth_token, 'Content-type': 'application/json'}
        self.apps = self.get_all_apps()

    def get_all_apps(self):
        response = requests.get(self.uri + '/service/marathon/v2/apps', headers=self.headers, verify=False).json()
        if response['apps'] ==[]:
            print ("No Apps found on Marathon")
            return None
        else:
            apps=[]
            for i in response['apps']:
                appid = i['id'].strip('/')
                apps.append(appid)
            print ("Found the following App LIST on Marathon =", apps)
            return apps

    def get_app_details(self, marathon_app):
        response = requests.get(self.uri + '/service/marathon/v2/apps/'+ marathon_app, headers=self.headers, verify=False).json()
        if (response['app']['tasks'] ==[]):
            print ('No task data on Marathon for App !', marathon_app)
            return None
        else:
            app_instances = response['app']['instances']
            self.appinstances = app_instances
            print(marathon_app, "has", self.appinstances, "deployed instances")
            app_task_dict={}
            for i in response['app']['tasks']:
                taskid = i['id']
                hostid = i['host']
                slaveId=i['slaveId']
                print ('DEBUG - taskId=', taskid +' running on '+hostid + 'which is Mesos Slave Id '+slaveId)
                app_task_dict[str(taskid)] = str(slaveId)
            return app_task_dict

    def scale_app(self,marathon_app,autoscale_multiplier):
        target_instances_float=self.appinstances * autoscale_multiplier
        target_instances=math.ceil(target_instances_float)
        if (target_instances > max_instances):
            print("Reached the set maximum instances of", max_instances)
            target_instances=max_instances
        else:
            target_instances=target_instances
        data ={'instances': target_instances}
        json_data=json.dumps(data)
        response=requests.put(self.uri + '/service/marathon/v2/apps/'+ marathon_app, data=json_data,headers=self.headers,verify=False)
        print ('Scale_app return status code =', response.status_code)


    def add_app(self,app_json_file):
        print(app_json_file)
        json_data= open(app_json_file).read()
        response=requests.post('{}{}'.format(self.uri, '/service/marathon/v2/apps'), data=json_data, headers=self.headers,verify=False)
        print ('Request =', response.json())
        if response.status_code !=201:
            print ('Add Marathon App FAILED  =', response.status_code)
        else:
            print ('Add Marathon App SUCCEEDED !  =', response.status_code)
        return response.json()['id']

def dcos_auth_login(dcos_master,userid,password):
    '''
    Will login to the DCOS ACS Service and RETURN A JWT TOKEN for subsequent API requests to Marathon, Mesos, etc
    '''
    rawdata = {'uid' : userid, 'password' : password}
    login_headers={'Content-type': 'application/json'}
    response = requests.post(dcos_master + '/acs/api/v1/auth/login', headers=login_headers, data=json.dumps(rawdata),verify=False).json()
    auth_token=response['token']
    return auth_token

