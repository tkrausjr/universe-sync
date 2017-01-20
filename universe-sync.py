__author__ = 'tkraus-m'

import requests
import sys
import subprocess

# Constants

remove_images=True # Will remove local copies of images already transferred to dst_registry_host
universe_image = '/Users/tkraus/gitHub/universe-sync/test-local-universe-01-18-17-v2.tar'
src_registry_proto = 'https://'
src_registry_host = 'localhost'
src_registry_port = 5000
src_http_port = 8083
src_insecure = True
pulled_images =[]

dst_registry_proto = 'http://'
dst_registry_host = '192.168.62.128'
dst_registry_port = 5000
dst_insecure = True

def load_universe(universe_image):
    print('--Loading Mesosphere/Universe Docker Image '+universe_image)
    command = ['docker', 'load', '-i' + universe_image]
    subprocess.check_call(command)

def start_universe(universe_image,command):

    print('--Starting Mesosphere/Universe Docker Image '+universe_image)
    subprocess.Popen(command).wait()

def get_registry_images(registry_proto,registry_host,registry_port):
    print("--Getting Mesosphere/Universe Repositories ")
    response = requests.get(registry_proto + registry_host + ':'+str(registry_port) +'/v2/_catalog', verify=False)

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
    command = ['docker', 'pull', name]

    subprocess.check_call(command)

def format_image_name(host, name):
    # Probably has a hostname at the front, get rid of it.
    print("--Formatting Image Name "+host+"/"+name)
    if '.' in name.split(':')[0]:
        return '{}/{}'.format(host, "/".join(name.split("/")[1:]))

    return '{}/{}'.format(host, name)

def tag_images(image,imagetag,fullImageId,dst_registry_host,dst_registry_port):

    print("--Tagging Image "+fullImageId + " for Destination Registry "+dst_registry_host+':'+str(dst_registry_port))

    command = ['docker', 'tag', fullImageId,
        format_image_name(dst_registry_host+':'+str(dst_registry_port),image)]
    subprocess.check_call(command)
    return command[3]

def push_images(new_image):
    print("--Pushing Image "+new_image)
    command = ['docker', 'push', new_image]
    subprocess.check_call(command)


def remove_images(fullImageRef,client,src_registry_host,src_registry_port):

    fullImageRefSplit = fullImageRef.split('/')
    dstimageHost= fullImageRefSplit[0]
    dstfullImage = fullImageRefSplit[1]

    # Remove Local Image Tagged for the Source Registry
    client.api.remove_image(fullImageRef,force=True)

    # Remove Local Image Tagged for the Target Registry
    client.api.remove_image(src_registry_host+ ':'+ str(src_registry_port) + '/' + dstfullImage, force=True)
    return

if __name__ == "__main__":

    registry_command = ['docker', 'run', '-d', '-p','5000:5000', '-e','REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt',
               '-e', 'REGISTRY_HTTP_TLS_KEY=/certs/domain.key', 'mesosphere/universe',
               'registry', 'serve', '/etc/docker/registry/config.yml']
    start_universe(universe_image,registry_command)

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
            push_images(new_image)
            new_images.append(new_image)
            print("Finished with Image ("+image+':'+imagetag+")\n")
        print("\n \n New Images uploaded to "+dst_registry_host+':'+str(dst_registry_port)+" are " + str(new_images))


    except (subprocess.CalledProcessError, urllib.error.HTTPError):
            print('MISSING Docker Images: {}')


    # HTTP ARTIFACT WORK

    http_docker_command = ['docker', 'run', '-d', '-p','8082:80', 'mesosphere/universe',
               'nginx', '-g', '"daemon off;"']
    start_universe(universe_image,http_docker_command)




    print("\n Program Finished \n" )