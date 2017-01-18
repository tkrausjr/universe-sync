__author__ = 'tkraus-m'

import docker
import requests
import sys

# Constants
remove_images=True # Will remove local copies of images already transferred to dst_registry_host
src_registry_host = 'localhost'
src_registry_port = 5001
src_http_port = 8083
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
    response = requests.get('https://'+ registry_host + ':'+str(registry_port) +'/v2/_catalog')

    if response.status_code != 200:
        print (str(response.status_code) + " Registry API CAll unsuccessful to " + registry_host + ':'+str(registry_port), Verify=False)
        print (" Raw Docker Error Message is  " + response.text )
        exit(1)
    #elif response == null:
    #    print ("No response. Source Registry Server is probably not available !")
    #    sys.exit(1)    
    else:
        responseJson=response.json()
        print("Response RAW JSON for Registry is" + str(responseJson))
        
        if responseJson['repositories'] ==[]:
            print ("No Images/Repositories found on Source Registry")
            sys.exit(1)
        else:
            repositories=[]
            for i in responseJson['repositories']:
                print("Found an image named " + i)
                repositories.append(i)
            return repositories

def get_registry_manifests(registry_host,registry_port,repos):
    registry_manifest_dict ={}
    print("get_registry_manifests Function")
    for i in repos:
            response = requests.get('https://'+ registry_host + ':'+str(registry_port) +'/v2/'+ i + '/tags/list', Verify=False)
            responseJson=response.json()
            print("Manifests Response " + str(responseJson))
            name = responseJson['name']
            tag = responseJson['tags'][0]
            registry_manifest_dict[str(name)] = str(tag)
            print("Name is " + name + " and tag is " + tag)
    return registry_manifest_dict

def pull_images(registry_host,registry_port,src_manifests,client):
    '''
    :param repos: Repositoires Python List returned from Registry API
    :param client: Docker-Py Module for initialized Client Object
    :return:
    '''
    images = []
    print("pull_images Function")
    for image,imagetag in src_manifests.items():
            #cpus_time =(task_stats['cpus_system_time_secs']+task_stats['cpus_user_time_secs'])
            #print ("Combined Task CPU Kernel and User Time for task", task, "=", cpus_time)
            print('Image in DICT = '+ image)
            print ('TAG in DICT = ' + imagetag)
            print("Pulling Image . . ." + image)
            client.images.pull(registry_host + ':'+str(registry_port) +'/' + image, tag=imagetag,stream=True)
            fullImageId = registry_host + ":" + str(registry_port) + "/" + image + ":" + imagetag
            print("Full Image ID = " + fullImageId)
            images.append(fullImageId)
    return images


def tag_images(pulled_images,client,dst_registry_host,dst_registry_port):
    '''
    Tag Images Function will use API call to local Docker Daemon to tag an image.
    :param repos: Repositoires Python List returned from Registry API
    :param client: Docker-Py Module for initialized Client Object
    :return:
    '''
    newImages = []
    for fullImageRef in pulled_images:
        print("Tagging Image . . ." + fullImageRef)
        fullImageRefSplit = fullImageRef.split('/')
        srcimageHost= fullImageRefSplit[0]
        srcfullImage = fullImageRefSplit[1]
        srcImageSplit = srcfullImage.split(':')
        srcImageName = srcImageSplit[0]
        srcImageTag = srcImageSplit[1]
        print ("**SPLIT SRC ImageHost = " + srcimageHost)
        print ("**SPLIT SRC ImageFullName = " +srcfullImage)
        print ("**SPLIT SRC srcImageName = " + srcImageName)
        print ("**SPLIT SRC srcImageTag = " +srcImageTag)
        newfullImageId = dst_registry_host + ":" + str(dst_registry_port) + "/" + srcImageName + ":" + srcImageTag
        client.api.tag(fullImageRef,dst_registry_host + ':'+ str(dst_registry_port)+'/'+srcImageName, tag=srcImageTag)
        newImages.append(newfullImageId)

    return newImages

def push_images(new_images,client):
    for fullImageRef in new_images:
        print("Pushing Image . . ." + fullImageRef)
        fullImageRefSplit = fullImageRef.split('/')
        dstimageHost= fullImageRefSplit[0]
        dstfullImage = fullImageRefSplit[1]
        dstImageSplit = dstfullImage.split(':')
        dstImageName = dstImageSplit[0]
        dstImageTag = dstImageSplit[1]
        print ("**SPLIT DST ImageHost = " + dstimageHost)
        print ("**SPLIT DST ImageFullName = " +dstfullImage)
        print ("**SPLIT DST srcImageName = " + dstImageName)
        print ("**SPLIT DST srcImageTag = " +dstImageTag)
        for line in client.images.push(fullImageRef,stream=True,insecure_registry=True):
            print (line)
        if remove_images==True:
            remove_images(fullImageRef,client,src_registry_host,src_registry_port)
    return new_images

def remove_images(fullImageRef,client,src_registry_host,src_registry_port):
    '''
    CURRENTLY NOT WORKING -- TEST in INTERACTIVE MODE !!!
    :param fullImageRef:
    :param client:
    :param src_registry_host:
    :param src_registry_port:
    :return:
    '''
    fullImageRefSplit = fullImageRef.split('/')
    dstimageHost= fullImageRefSplit[0]
    dstfullImage = fullImageRefSplit[1]

    # Remove Local Image Tagged for the Source Registry
    client.api.remove_image(fullImageRef,force=True)

    # Remove Local Image Tagged for the Target Registry
    client.api.remove_image(src_registry_host+ ':'+ str(src_registry_port) + '/' + dstfullImage, force=True)
    return

if __name__ == "__main__":

    src_repos = get_registry_images(src_registry_host,src_registry_port)

    src_manifests = get_registry_manifests(src_registry_host,src_registry_port,src_repos)

    pulled_images = pull_images(src_registry_host,src_registry_port,src_manifests,docker_client)

    print("Pulled Images = " + str(pulled_images))

    new_images = tag_images(pulled_images,docker_client,dst_registry_host,dst_registry_port)

    pushed_images = push_images(new_images,docker_client)

    print("MAIN - Registry Manifests = " + str(src_manifests))
    print("MAIN - New Images = " + str(new_images))



    " ----BEGIN RUN TESTING SECTION----WORKING "
    print ("3-TESTING Local Image LIST !!! ")
    imagesList=()
    imagesList = docker_client.images.list()
    print ("OUTPUT - List of Local Images = " + str(imagesList))

    " There is a known issue with images with a NULL TAG -- See Evernote !!! "

    " -----END RUN TESTING SECTION-----WORKING "


    " -----END RUN TESTING SECTION-----WORKING "
    print ("Program COMPLETE !!!! ")