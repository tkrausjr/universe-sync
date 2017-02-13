__author__ = 'tkraus-m'

import requests
import sys
import subprocess
import time
import json
import os
import fileinput

# Set the Target for Docker Iamges. Valid options are 'quay' and 'docker_registry'
docker_target = 'quay'
# Set the Target for HTTP Artifacts including the actual Universe JSON definition itself
# Valid options are 'nginx' and 'nexus'
http_target = 'nexus'

remove_images=True # Will remove local copies of images already transferred to dst_registry_host
universe_image = '/Users/tkraus/test-local-universe-01-23-17-v1.tar'
src_registry_proto = 'https://'
src_registry_host = 'localhost:5000'
src_http_protocol = 'http://'
src_http_host = 'localhost:8082'
src_insecure = True
pulled_images =[]

http_proxy ='gieproxy.gielab.jpmchase.net:8080'
https_proxy = http_proxy
proxies = {"http" : http_proxy, "https" : https_proxy}

dst_registry_proto = 'http://'
dst_registry_host = '192.168.62.128:5000'
dst_registry_namespace ='universe'

dst_http_protocol ='https://'
dst_http_host = '192.168.62.128'
# dst_http_port = '443'
dst_http_namespace = 'maven/content/sites/GCP-SITE'
dst_http_repository_user = 'admin'
dst_http_repository_pass = 'admin123'
new_universe_json_file = 'tk-universe.json'
working_directory = '/Users/tkraus/gitHub/universe-sync/data/'

def load_universe(universe_image):
    print('--Loading Mesosphere/Universe Docker Image '+universe_image)
    command = ['docker', 'load', '-i', universe_image]
    subprocess.check_call(command)

def start_universe(universe_image,command):

    print('--Starting Mesosphere/Universe Docker Image '+universe_image)

    subprocess.Popen(command).wait()
    # subprocess.check_call(command,stdout=None,stderr=Exception)
    print('--Successfully Started Mesosphere/Universe Docker Image '+universe_image)
    print('--Waiting 5 Seconds for Container Startup')
    time.sleep(5)

def get_registry_images(registry_proto,registry_host):
    print("--Getting Mesosphere/Universe Repositories ")
    response = requests.get(registry_proto + registry_host +'/v2/_catalog', verify=False)

    if response.status_code != 200:
        print (str(response.status_code) + " Registry API CAll unsuccessful to " + registry_host)
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

def get_registry_manifests(registry_proto,registry_host,repos):
    registry_manifest_dict ={}
    print("--Getting Source Mesosphere/Universe Registry Manifests")
    for i in repos:
            response = requests.get(registry_proto + registry_host +'/v2/'+ i + '/tags/list', verify=False)
            responseJson=response.json()
            print("----Manifests Response " + str(responseJson))
            name = responseJson['name']
            tag = responseJson['tags'][0]
            registry_manifest_dict[str(name)] = str(tag)
            print("----Name is " + name + " and tag is " + tag)
    return registry_manifest_dict

def pull_images(name):
    print('--Pulling docker image: {}'.format(name))
    command = ['docker', 'pull', name]

    subprocess.check_call(command)

## Start -JPMC Changes needed for missing TAG in target REPO
def new_format_image_name(dst_registry_host,dst_registry_namespace,image,imagetag):
    print("Src Imagename is " + image)
    if '/' in image:
        newimage='{}/{}/{}:{}'.format(dst_registry_host,dst_registry_namespace,image.split("/")[1],imagetag)
        print("Slash in image name, New image is " + newimage)
        return newimage

    else:
        print("No slash in image so New image is " + newimage)
        return image
## Stop JPMC Changes needed for missing TAG in target REPO

def tag_images(image,imagetag,fullImageId,dst_registry_host):

    new_image_name = new_format_image_name(dst_registry_host,dst_registry_namespace,image,imagetag)
    print("--Tagging temp Universe Image "+fullImageId + " for new Registry "+new_image_name)
    command = ['docker', 'tag', fullImageId, new_image_name]
    subprocess.check_call(command)
    return new_image_name


def push_images(new_image,docker_target):
    if docker_target == 'docker_registry':
        print("--Pushing Image to Docker Registry - "+new_image)
        command = ['docker', 'push', new_image]
        subprocess.check_call(command)
    if docker_target == 'quay':
        print("--Pushing Image to Quay - "+new_image)
        command = ['docker', 'push', new_image]
        subprocess.check_call(command)

def copy_http_data(working_directory,new_universe_json_file):
    print("--Copying Universe HTTP to hosts Working Directory ")
    command = ['docker', 'cp', 'universe-registry:/usr/share/nginx/html/', working_directory]
    subprocess.check_output(command)

    #command = ['sudo', 'chown', '-R', 'tkraus-m:', working_directory]
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
            if file.startswith(".") or file.startswith("index.html") or file.startswith("domain.crt"):
                print("Found files to skip = " + file)

            else:
                print("Files are " +os.path.join(subdir, file))
                http_artifacts.append(os.path.join(subdir, file))
    return http_artifacts

def upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_namespace,http_artifacts):

    baseurl ='{}{}/{}/{}'.format(dst_http_protocol,dst_http_host,dst_http_namespace,time.strftime("%Y-%m-%d"))
    for file in http_artifacts:
        print('\nWorking on file ' + file)
        upload_file={'file' : open(file,'rb')}
        pathurl=(file.split("html/")[1])
        url = '{}{}'.format(baseurl,pathurl)
        print(' Updated URL for Upload = {}{}'.format(baseurl,pathurl))
        
        headers = {'Connection':'keep-alive','content-type': 'multipart/form-data'}
        with open(file,'rb') as uploadfile:
            response = requests.put(url, data=uploadfile, auth=(dst_http_repository_user,dst_http_repository_pass),headers=headers,proxies=proxies)
        
        if response.status_code != 201:
            print ("  "+str(response.status_code) + " -- Nexus API CAll unsuccessful to " + url)
            print (response.raise_for_status())
            exit(1)
        else:
            print ("  "+str(response.status_code) + " -- Nexus API CAll SUCCESS to " + url)
    return baseurl
    
def clean_up_host():
    command = ['sudo', 'docker', 'rm', '-f', 'universe-registry']
    subprocess.check_call(command)

    command = ['rm', '-rf', './data/*']
    subprocess.check_call(command)

if __name__ == "__main__":
    
    print('universe-sync-jpmc.py Program RUNNING . . .  ')
    # Temporarily removed line below
    load_universe(universe_image)
    registry_command = ['docker', 'run', '-d', '--name', 'universe-registry', '-v', '/usr/share/nginx/html/','-p','5000:5000', '-e','REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt',
               '-e', 'REGISTRY_HTTP_TLS_KEY=/certs/domain.key', 'mesosphere/universe',
               'registry', 'serve', '/etc/docker/registry/config.yml']
    start_universe(universe_image,registry_command)
    
    # DOCKER REPO IMAGE MOVE from UNIVERSE IMAGE to DEST REGISTRY
    src_repos = get_registry_images(src_registry_proto,src_registry_host)
    src_manifests = get_registry_manifests(src_registry_proto,src_registry_host,src_repos)
   
    try:
        # JPMC START FIX BELOW
        old_new_image_dict = {}
        # *** JPMC END FIX  ***
        for image,imagetag in src_manifests.items():
            print('Starting on Image ('+image+':'+imagetag+")")
            fullImageId = src_registry_host + "/" + image + ":" + imagetag
            print("Source Docker Image to Pull = " + fullImageId)
            pull_images(fullImageId)
            new_image=tag_images(image,imagetag,fullImageId,dst_registry_host)
            print("Destination Docker Image to Push = " + new_image)
            push_images(new_image,docker_target)

            # *** JPMC START FIX BELOW ***
            old_new_image_dict[fullImageId] = new_image
            print("Finished with Image ("+image+':'+imagetag+")\n")
            # *** JPMC END FIX  ***

        print("\n \n New Images uploaded to "+dst_registry_host+ " are " + str(old_new_image_dict.items()))

    except (subprocess.CalledProcessError):
            print('MISSING Docker Images: {}')
    
    # HTTP Artifacts
    # Copy out the entire nginx / html directory to data directory where script is being run.

    updated_universe_json_file = copy_http_data(working_directory,new_universe_json_file)

    # HTTP Artifacts - Rewrite the universe.json file with correct Docker and HTTP URL's
    # 3 Lines below are unnecessary if using SED and
    with open(working_directory + 'html/repo-up-to-1.8.json') as json_data:
        src_universe_json = json.load(json_data)
        print("Original Universe JSON = " + str(src_universe_json))

    # *** JPMC START FIX BELOW ***

    # *** JPMC START FIX BELOW *** - CORRECTED REPLACEMENT of DOCKER IMAGES in Universe File
    for fullImageId,new_image in old_new_image_dict.items():
        transform_universe_json(fullImageId,new_image,working_directory,updated_universe_json_file)
    # *** JPMC END FIX  *** -

    transform_universe_json(src_http_host,dst_http_host,working_directory,updated_universe_json_file)

    with open(updated_universe_json_file) as json_data:
        new_universe_json = json.load(json_data)
        print("NEW Universe JSON = " + str(new_universe_json))

    '''
    # Return a LIST of all Absolute File References for upload to HTTP Repository
    http_artifacts = return_http_artifacts(working_directory)
    print("Cleaned up HTTP Artifacts are " + str(http_artifacts))


    #Note tested yet not working - needs some work
    print ("\n Configured HTTP Repository is " + http_target)
    if http_target == 'nexus':
        baseurl = upload_http_nexus(dst_http_protocol,dst_http_host,dst_http_namespace,http_artifacts)
    elif http_target == 'artifactory':
        baseurl = upload_http_artifactory()
    else:
        print("Configured HTTP Repsitory is not supported -- " + http_target)
    '''
    print("\n Program Finished \n" )
    # Clean up Containers and HTTP Data Directory
    # clean_up_host()
    print("\n ********************* \n" )
    print("\n ********************* \n" )
    print('To load the new Universe use the DCOS CLI command')
    print('{} {} {}{}'.format('dcos package repo add','<repo-name>', baseurl, new_universe_json_file ))
