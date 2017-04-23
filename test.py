__author__ = 'tkraus-m'



import sys
import requests
import json
import marathon

'''
dcos_master = input("Enter the DNS hostname or IP of your Marathon Instance : ")
userid = input('Enter the username for the DCOS cluster : ')
password = input('Enter the password for the DCOS cluster : ')
'''
dcos_master = 'https://72.83.34.30'
userid = 'justin'
password = 'thisismypassword'

marathon_app_json = '/Users/tkraus/sandbox/marathon/12b-siege.json'

## Login to DCOS to retrieve an API TOKEN
dcos_token = marathon.dcos_auth_login(dcos_master,userid,password)
if dcos_token != '':
    print('{}{}'.format("DCOS TOKEN = ", dcos_token))
else:
    exit(1)
print('-----------------------------')

## Initialize new Marathon Instance of Marathon Class
new_marathon = marathon.marathon(dcos_master,dcos_token)

## List Marathon Apps Method
marathon_apps = new_marathon.get_all_apps()
print ("The following apps exist in Marathon...", marathon_apps)
print('-----------------------------')

## Get Marathon App Details Method - List Tasks & Agents for all Marathon Apps
if marathon_apps != None:
    for app in marathon_apps:
        app_details = new_marathon.get_app_details(app)
        print('{}{}'.format("Marathon App details = ", app_details))
        print('-----------------------------')

new_app = new_marathon.add_app(marathon_app_json)
print('Marathon App ID is ' + new_app)
