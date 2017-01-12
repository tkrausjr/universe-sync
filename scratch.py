__author__ = 'tkraus-m'

import docker
import requests

# Constants
src_registry_host = 'localhost'
src_registry_port = 5000
docker_client = docker.from_env()


if __name__ == "__main__":



    " ----BEGIN RUN TESTING SECTION----WORKING "
    print ("1-Testing Docker RUN World !!!")
    docker_client.containers.run("alpine", "echo HELLO WORLD !!!! It works in Python universe-sync app")
    " -----END RUN TESTING SECTION-----WORKING "


    " ----BEGIN PULL TESTING SECTION----WORKING "
    print ("2-TESTING Image Pull !!!")
    docker_client.images.pull("alpine")
    " -----END RUN TESTING SECTION-----WORKING "


    " ----BEGIN RUN TESTING SECTION----WORKING "
    print ("3-TESTING Local Image LIST !!! ")
    imagesList=()
    imagesList = docker_client.images.list()
    print ("OUTPUT - List of Local Images = " + str(imagesList))

    " There is a known issue with images with a NULL TAG -- See Evernote !!! "

    " -----END RUN TESTING SECTION-----WORKING "




    " -----END RUN TESTING SECTION-----WORKING "
    print ("Program COMPLETE !!!! ")