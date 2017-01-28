__author__ = 'tkraus-m'

import requests
import sys
import subprocess
import time
import json
import os
import fileinput

# Constants

# Set the Target for Docker Iamges
# Valid options are 'quay' and 'docker_registry'

docker_target = 'quay'
# Set the Target for HTTP Artifacts including the actual Universe JSON definition itself
# Valid options are 'nginx' and 'nexus'
http_target = 'nexus'

remove_images=True # Will remove local copies of images already transferred to dst_registry_host
universe_image = '/Users/tkraus/test-local-universe-01-23-17-v1.tar'
src_registry_proto = 'https://'
src_registry_host = 'localhost'
src_registry_port = 5005
src_http_protocol = 'http://'
src_http_port = 8082
src_insecure = True
pulled_images =[]

http_proxy ='gieproxy.gielab.jpmchase.net:8080'
https_proxy = http_proxy
proxies = {"http" : http_proxy, "https" : https_proxy}

dst_registry_proto = 'http://'
dst_registry_host = '192.168.62.128'
dst_registry_port = 5000
dst_registry_namespace ='universe'

dst_http_protocol ='https://'
dst_http_host = 'repo.jpmchase.net'
dst_http_port = '443'
dst_http_namespace = 'maven/content/sites/GCP-SITE/scripts1'
dst_http_repository_user = 'O665494'
dst_http_repository_pass = 'Ah&i6Bzo1V'
new_universe_json_file = 'tk-universe.json'
working_directory = '/var/lib/a_ansible/github/universe-sync/data/'

def load_universe(universe_image):
    print('--Loading Mesosphere/Universe Docker Image '+universe_image)
    command = ['sudo','docker', 'load', '-i' + universe_image]
    subprocess.check_call(command)

def start_universe(universe_image,command):

    print('--Starting Mesosphere/Universe Docker Image '+universe_image)

    subprocess.Popen(command).wait()
    # subprocess.check_call(command,stdout=None,stderr=Exception)
    print('--Successfully Started Mesosphere/Universe Docker Image '+universe_image)
    print('--Waiting 5 Seconds for Container Startup')
    time.sleep(5)

def get_registry_images(registry_proto,registry_host,registry_port):
    print("--Getting Mesosphere/Universe Repositories ")
    response = requests.get(registry_proto + registry_host + ':'+str(registry_port) +'/v2/_catalog', proxies=proxies, verify=False)

    if response.status_code != 200:
        print (str(response.status_code) + " Registry API CAll unsuccessful to " + registry_host + ':'+str(registry_port))
        print ("----Raw Docker Error Message is  " + response.text )
        exit(1)
    else:
        responseJson=response.json()
        if responseJson['repositories'] ==[]:
            print ("----No Repositories found on Source Mesosphere/Universe")
            sys.exit(1)
        else:
            repositories=[]
            for i in responseJson['repositories']:
                print("----Found an image named " + i)
                repositories.append(i)
            return repositories

def get_registry_manifests(registry_proto,registry_host,registry_port,repos):
    registry_manifest_dict ={}
    print("--Getting Source Mesosphere/Universe Registry Manifests")
    for i in repos:
            response = requests.get(registry_proto + registry_host + ':'+str(registry_port) +'/v2/'+ i + '/tags/list', verify=False)
            responseJson=response.json()
            print("----Manifests Response " + str(responseJson))
            name = responseJson['name']
            tag = responseJson['tags'][0]
            registry_manifest_dict[str(name)] = str(tag)
            print("----Name is " + name + " and tag is " + tag)
    return registry_manifest_dict

def pull_images(name):
    print('--Pulling docker image: {}'.format(name))
    command = ['sudo', 'docker', 'pull', name]

    subprocess.check_call(command)

def format_image_name(host, name):
    # Probably has a hostname at the front, get rid of it.
    print("--Formatting Image Name "+host+"/"+name)
    if '.' in name.split(':')[0]:
        return '{}/{}'.format(host, "/".join(name.split("/")[1:]))

    return '{}/{}'.format(host, name)

def new_format_image_name(dst_registry_host,dst_registry_port,dst_registry_namespace,image):
    print("Src Imagename is " + image)
    if '/' in image:
        newimage='{}:{}/{}/{}'.format(dst_registry_host,dst_registry_port,dst_registry_namespace,image.split("/")[1])
        print("New image is " + newimage)
        return newimage

    return image

def tag_images(image,imagetag,fullImageId,dst_registry_host,dst_registry_port):

    print("--Tagging Universe Image "+fullImageId + " for Destination Registry "+dst_registry_host+':'+str(dst_registry_port))
    command = ['sudo', 'docker', 'tag', fullImageId,
        new_format_image_name(dst_registry_host,dst_registry_port,dst_registry_namespace,image)]
        # format_image_name(dst_registry_host+':'+str(dst_registry_port),image)]
    subprocess.check_call(command)
    return command[3]

def push_images(new_image,docker_target):
    if docker_target == 'docker_registry':
        print("--Pushing Image to Docker Registry - "+new_image)
        command = ['sudo', 'docker', 'push', new_image]
        subprocess.check_call(command)
    if docker_target == 'quay':
        print("--Pushing Image to Quay - "+new_image)
        command = ['sudo', 'docker', 'push', new_image]
        subprocess.check_call(command)

def copy_http_data(working_directory,new_universe_json_file):
    print("--Copying Universe HTTP to hosts Working Directory ")
    command = ['sudo', 'docker', 'cp', 'universe-registry:/usr/share/nginx/html/', working_directory]
    subprocess.check_output(command)

    command = ['sudo', 'chown', '-R', 'a_ansible:users', working_directory]
    subprocess.check_output(command)
       
    updated_universe_json_file = (working_directory +'html/'+ new_universe_json_file)
    command = ['cp', working_directory + 'html/universe.json', updated_universe_json_file ]
    subprocess.check_output(command)
    return updated_universe_json_file  # Return updated reference to the now modified Universe.json file


def transform_universe_json(src_string,dst_string,working_directory,updated_universe_json_file):
    for line in fileinput.input(updated_universe_json_file, inplace=True):
        # inside this loop the STDOUT will be redirected to the file
        # the comma after each print statement is needed to avoid double line breaks
        print(line.replace(src_string,dst_string)),

def write_new_universe_json(new_universe_json):
    with open('./data/tk-universe.json', 'w') as outfile:
        json.dump(new_universe_json, outfile)

def return_http_artifacts(working_directory):
    http_artifacts = []
    os.chdir(working_directory)
    for subdir, dirs, files in os.walk(working_directory):
        for file in files:
            if file.startswith("repo-") or file.startswith(".") or file.startswith("index.html") or file.startswith("domain.crt"):
                print("Found files to skip = " + file)

            else:
                print("Files are " +os.path.join(subdir, file))
                http_artifacts.append(os.path.join(subdir, file))
    return http_artifacts

def upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_port,dst_http_namespace,http_artifacts):

    baseurl ='{}{}:{}/{}/'.format(dst_http_protocol,dst_http_host,dst_http_port,dst_http_namespace)
    for file in http_artifacts:
        print('\n ********** WORKING ON A NEW FILE IN THE LOOP*********\n' + file)
        upload_file={'file' : open(file,'rb')}
        pathurl=(file.split("html/")[1])
        print("First pathurl = "+pathurl)
        if len(pathurl.rsplit('/',1)) > 1:
            url = '{}{}/'.format(baseurl,pathurl.rsplit('/',1)[0 ])
            print("+++++ STEP 2 needed, url= "+url)
            response = requests.post(url, auth=(dst_http_repository_user,dst_http_repository_pass),proxies=proxies,verify=False)

        else:
            url = baseurl
            print("+++++ STEP 2 NOT needed, baseurl= "+url)

        headers = {'Connection':'keep-alive','content-type': 'multipart/form-data'}
        response = requests.put(url, files=upload_file, auth=(dst_http_repository_user,dst_http_repository_pass),proxies=proxies,headers=headers,verify=False)
        print (response.raw)
        print (response.request)
        print (str(response.status_code))


        if response.status_code != 201:
            print (str(response.status_code) + " Registry API CAll unsuccessful to " + url)
            print(response.content)
            print(response.headers)
            print ("----Raw Nexus Error Message is  " + response.text )
            exit(1)
        else:
            print (str(response.status_code) + " Registry API CAll SUCCESS to " + url)
            print(response.content)
            print(response.headers)
            print ("----Raw Nexus Error Message is  " + response.text )

def clean_up_host():
    command = ['sudo', 'docker', 'rm', '-f', 'universe-registry']
    subprocess.check_call(command)

    command = ['rm', '-rf', './data/*']
    subprocess.check_call(command)

if __name__ == "__main__":
    
    # Temporarily removed line below
    # load_universe(universe_image)
    registry_command = ['sudo', 'docker', 'run', '-d', '--name', 'universe-registry', '-v', '/usr/share/nginx/html/','-p','5005:5000', '-e','REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt',
               '-e', 'REGISTRY_HTTP_TLS_KEY=/certs/domain.key', 'mesosphere/universe',
               'registry', 'serve', '/etc/docker/registry/config.yml']
    start_universe(universe_image,registry_command)
    '''
    # DOCKER REPO IMAGE MOVE from UNIVERSE IMAGE to DEST REGISTRY
    src_repos = get_registry_images(src_registry_proto,src_registry_host,src_registry_port)
    src_manifests = get_registry_manifests(src_registry_proto,src_registry_host,src_registry_port,src_repos)
   
    try:
        new_images = []
        for image,imagetag in src_manifests.items():
            print('Starting on Image ('+image+':'+imagetag+")")
            fullImageId = src_registry_host + ":" + str(src_registry_port) + "/" + image + ":" + imagetag
            print("Source Docker Image to Pull = " + fullImageId)
            pull_images(fullImageId)
            new_image=tag_images(image,imagetag,fullImageId,dst_registry_host,dst_registry_port)
            print("Destination Docker Image to Push = " + new_image)
            push_images(new_image,docker_target)
            new_images.append(new_image)
            print("Finished with Image ("+image+':'+imagetag+")\n")
        print("\n \n New Images uploaded to "+dst_registry_host+':'+str(dst_registry_port)+" are " + str(new_images))

    except (subprocess.CalledProcessError, urllib.error.HTTPError):
            print('MISSING Docker Images: {}')
    '''
    # HTTP Artifacts
    # Copy out the entire nginx / html directory to data directory where script is being run.

    updated_universe_json_file = copy_http_data(working_directory,new_universe_json_file)

    # HTTP Artifacts - Rewrite the universe.json file with correct Docker and HTTP URL's
    # 3 Lines below are unnecessary if using SED and
    with open(working_directory + 'html/universe.json') as json_data:
        src_universe_json = json.load(json_data)
        print("Source Universe JSON = " + str(src_universe_json))

    src_registry_str = src_registry_host +':'+ str(src_registry_port)
    dst_registry_str = dst_registry_host +':'+ str(dst_registry_port)
    src_http_str = src_http_protocol + src_registry_host +':'+ str(src_http_port)
    dst_http_str = dst_http_protocol + dst_http_host

    print("\n Source Registry String = " + src_registry_str)
    print("Destination Registry String = " + dst_registry_str)
    print("Source HTTP String = " + src_http_str)
    print("Destination HTTP String = " + dst_http_str)

    transform_universe_json(src_registry_str,dst_registry_str,working_directory,updated_universe_json_file)
    transform_universe_json(src_http_str,dst_http_str,working_directory,updated_universe_json_file)

    with open(updated_universe_json_file) as json_data:
        new_universe_json = json.load(json_data)
        print("Updated Universe JSON = " + str(new_universe_json))


    # Return a LIST of all Absolute File References for upload to HTTP Repository
    http_artifacts = return_http_artifacts(working_directory)
    print("Cleaned up HTTP Artifacts are " + str(http_artifacts))


    #Note tested yet not working - needs some work
    print ("\n Configured HTTP Repository is " + http_target)
    if http_target == 'nexus':
        upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_port,dst_http_namespace,http_artifacts)
    elif http_target == 'artifactory':
        upload_http_artifactory()
    else:
        print("Configured HTTP Repsitory is not supported -- " + http_target)

    # Clean up Containers and HTTP Data Directory
    # clean_up_host()
    print("\n Program Finished \n" )


