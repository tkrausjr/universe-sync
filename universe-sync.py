__author__ = 'tkraus-m'

import docker
import requests
import sys

# Constants
src_registry_host = 'localhost'
src_registry_port = 5000
docker_client = docker.from_env()
pulled_images =[]

dst_registry_host = 'localhost'
dst_registry_port = 5001


def get_registry_images(registry_host,registry_port):
    '''
    :param registry_host: The hostname of the Docker Registry Server
    :param registry_port: THE TCP Port the Docker Registry Server is listening on
    :return:
    '''
    print("get_registry_images Function")
    response = requests.get('http://'+ registry_host + ':'+str(registry_port) +'/v2/_catalog')
    responseJson=response.json()

    if response.status_code != 200:
        print (str(response.status) + " Registry API CAll unsuccessful to " + registry_host + ':'+registry_port)
        exit(1)
    elif responseJson['repositories'] ==[]:
        print ("No Images/Repositories found on Source Registry")
        sys.exit(1)
    else:
        print("Response RAW JSON for Registry is" + str(responseJson))
        repositories=[]
        for i in responseJson['repositories']:
            print("Found an image named " + i)
            repositories.append(i)
        return repositories

def get_registry_manifests(registry_host,registry_port,repos):
    print("get_registry_manifests Function")
    for i in repos:
            response = requests.get('http://'+ registry_host + ':'+str(registry_port) +'/v2/'+ i + '/tags/list')
            responseJson=response.json()
            print("Manifests Response " + str(responseJson))

    return responseJson

def pull_images(registry_host,registry_port,repos,client):
    '''
    :param repos: Repositoires Python List returned from Registry API
    :param client: Docker-Py Module for initialized Client Object
    :return:
    '''
    images = []
    print("pull_images Function")
    for i in repos:

        print("Pulling Image . . ." + i)
        client.images.pull(registry_host + ':'+str(registry_port) +'/' + i, tag='latest')
        fullImageId = registry_host + ":" + str(registry_port) + "/" + i + ":" + "latest"
        print("Full Image ID = " + fullImageId)
        images.append(fullImageId)
    return images


def tag_images(images,client):
    '''
    Tag Images Function will use API call to local Docker Daemon to tag an image.
    :param repos: Repositoires Python List returned from Registry API
    :param client: Docker-Py Module for initialized Client Object
    :return:
    '''
    for i in images:
        print("Tagging Image . . ." + i)

        image = client.images.get(i)
        print("Image Attributes are " + str(image.attrs))


    return


if __name__ == "__main__":

    src_repos = get_registry_images(src_registry_host,src_registry_port)

    src_manifests = get_registry_manifests(src_registry_host,src_registry_port,src_repos)

    pulled_images = pull_images(src_registry_host,src_registry_port,src_repos,docker_client)

    print("Pulled Images = " + str(pulled_images))

    tag_images(pulled_images,docker_client)

    print("MAIN - Registry Manifests = " + str(src_manifests))




    " ----BEGIN RUN TESTING SECTION----WORKING "
    print ("3-TESTING Local Image LIST !!! ")
    imagesList=()
    imagesList = docker_client.images.list()
    print ("OUTPUT - List of Local Images = " + str(imagesList))

    " There is a known issue with images with a NULL TAG -- See Evernote !!! "

    " -----END RUN TESTING SECTION-----WORKING "


    " -----END RUN TESTING SECTION-----WORKING "
    print ("Program COMPLETE !!!! ")