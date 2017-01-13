#!/usr/bin/env python3

import argparse
import concurrent.futures
import contextlib
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

HTTP_ROOT = "http://nexus.mshome:8082/"
DOCKER_ROOT = "quay.mshome:5000"

def main():
    # Docker writes files into the tempdir as root, you need to be running
    # the script as root to clean these up successfully.
    if os.getuid() != 0:
        print("You must run this as root, please `sudo` first.")
        sys.exit(1)

    # jsonschema is required by the universe build process, make sure it is
    # installed before running.
    if not shutil.which("jsonschema"):
        print("You must first install jsonschema (pip install jsonschema).")
        sys.exit(1)

    # cosmos requires directories to be saved. python does it only sometimes.
    # Use zip to make sure it works.
    if not shutil.which("zip"):
        print("You must first install `zip`.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='This script is able to download the latest artifacts for '
        'all of the packages in the Universe repository into a zipfile. It '
        'uses a temporary file to store all of the artifacts as it downloads '
        'them because of this it requires that your temporary filesystem has '
        'enough space to store all of the artifact. You can control the path '
        'to the temporary file by setting the TMPDIR environment variable. '
        'E.g. TMPDIR=\'.\' ./scripts/local-universe.py ...')
    parser.add_argument(
        '--repository',
        required=True,
        help='Path to the top level package directory. E.g. repo/packages')
    parser.add_argument(
        '--include',
        default='',
        help='Command separated list of packages to include. If this option '
        'is not specified then all packages are downloaded. E.g. '
        '--include="marathon,chronos"')
    parser.add_argument(
        '--selected',
        action='store_true',
        default=False,
        help='Set this to include only selected packages')

    args = parser.parse_args()

    package_names = [name for name in args.include.split(',') if name != '']

    ### TK Added 1 line below
    dockerimages = list()
    print(' Target Docker Registry is ' + DOCKER_ROOT)


    outputbasedir=os.path.curdir
    outputdir=outputbasedir + '/'+ 'output'
    print("Output path = " + outputdir)
    dir_path = tempfile.TemporaryDirectory()
    http_artifacts = dir_path.name / pathlib.Path("http")
    docker_artifacts = dir_path.name
    repo_artifacts = dir_path.name / pathlib.Path("universe/repo/packages")

    os.makedirs(str(http_artifacts))
    os.makedirs(str(repo_artifacts))

    failed_packages = []
    def handle_package(opts):
        package, path = opts
        try:
            prepare_repository(package, path, pathlib.Path(args.repository),
                repo_artifacts)

            for url, archive_path in enumerate_http_resources(package, path):
                add_http_resource(http_artifacts, url, archive_path)

            for name in enumerate_docker_images(path):
                ### Ultimately localhost:5000 should be replaced by DOCKER_ROOT variable
                ### TK Added 2 line below

                print("Docker pull ImageName = " + name)

                download_docker_image(name)

                outname=(name.replace('/','_')+'.tar')
                if outname.startswith('docker.io'):
                    outname=outname[10:]
                print ("Docker save filename = " + outname)
                dockerimages.append(outname)
                save_docker_image(docker_artifacts,outname,name)

        except (subprocess.CalledProcessError, urllib.error.HTTPError):
            print('MISSING ASSETS: {}'.format(package))
            remove_package(package, dir_path)
            failed_packages.append(package)

        return package

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for package in executor.map(handle_package,
                enumerate_dcos_packages(
                    pathlib.Path(args.repository),
                    package_names,
                    args.selected)):
            print("Completed: {}".format(package))

    # TK added 1 line below to call the Docker images function
    copy_output(dir_path,dockerimages,outputdir,HTTP_ROOT,DOCKER_ROOT)

    if failed_packages:
        print("Errors: {}".format(failed_packages))
        print("These packages are not included in the image.")

def enumerate_dcos_packages(packages_path, package_names, only_selected):
    """Enumarate all of the package and revision to include
    :param packages_path: the path to the root of the packages
    :type pacakges_path: str
    :param package_names: list of package to include. empty list means all
                         packages
    :type package_names: [str]
    :param only_selected: filter the list of packages to only ones that are
                          selected
    :type only_selected: boolean
    :returns: generator of package name and revision
    :rtype: gen((str, str))
    """

    for letter_path in packages_path.iterdir():
        assert len(letter_path.name) == 1 and letter_path.name.isupper()
        for package_path in letter_path.iterdir():

            largest_revision = max(
                package_path.iterdir(),
                key=lambda revision: int(revision.name))


            if only_selected:
                with (largest_revision / 'package.json').open() as json_file:
                    if json.load(json_file).get('selected', False):
                        yield (package_path.name, largest_revision)

            elif not package_names or package_path.name in package_names:
                # Enumerate package if list is empty or package name in list
                yield (package_path.name, largest_revision)


def enumerate_http_resources(package, package_path):
    with (package_path / 'resource.json').open() as json_file:
        resource = json.load(json_file)

    for name, url in resource.get('images', {}).items():
        if name != 'screenshots':
            yield url, pathlib.Path(package, 'images')

    for name, url in resource.get('assets', {}).get('uris', {}).items():
        yield url, pathlib.Path(package, 'uris')

    command_path = (package_path / 'command.json')
    if command_path.exists():
        with command_path.open() as json_file:
            commands = json.load(json_file)

        for url in commands.get("pip", []):
            yield url, pathlib.Path(package, 'commands')

def enumerate_docker_images(package_path):
    with (package_path / 'resource.json').open() as json_file:
        resource = json.load(json_file)

    dockers = resource.get('assets', {}).get('container', {}).get('docker', {})

    return (name for _, name in dockers.items())

@contextlib.contextmanager

def download_docker_image(name):
    print('Pull docker images: {}'.format(name))
    command = ['docker', 'pull', name]
    subprocess.check_call(command)

def format_image_name(host, name):
    # Probably has a hostname at the front, get rid of it.
    print("Name = " + name)
    if '.' in name.split(':')[0]:
        return '{}/{}'.format(host, "/".join(name.split("/")[1:]))
    return '{}/{}'.format(host, name)

def save_docker_image(docker_artifacts,outname,name):
    print('Saving docker image: {}'.format(outname))
    fullpath = docker_artifacts + '/'+ outname
    command = ['docker', 'save', '-o', fullpath, name]
    separator = ' '
    print("TK-Docker save Command to run is " + separator.join(command))
    subprocess.check_call(command)

# TK Lines below copy the docker_image_manifest, docker image tarballs, and http artifacts
############################
def copy_output(dir_path,dockerimages,outputdir,HTTP_ROOT,DOCKER_ROOT):
    print ('Creating Docker Image Manifest')
    fileobj = open(dir_path.name +'/'+'dockerimages.txt', 'wt')
    print('--------------------------------------------------',file=fileobj)
    print('HTTP_ROOT='+HTTP_ROOT,file=fileobj)
    print('DOCKER_ROOT='+DOCKER_ROOT,file=fileobj)
    print('--------------------------------------------------',file=fileobj)
    for image in dockerimages:
        print('Docker Image is : ' + image)
        print(image,file=fileobj)
    fileobj.close()
    print ('Moving Artifacts to Output Directory')
    shutil.copytree(dir_path.name, outputdir)

def add_http_resource(dir_path, url, base_path):
    archive_path = (dir_path / base_path /
        pathlib.Path(urllib.parse.urlparse(url).path).name)
    print('Adding {} at {}.'.format(url, archive_path))
    os.makedirs(str(archive_path.parent), exist_ok=True)
    urllib.request.urlretrieve(url, str(archive_path))

def prepare_repository(package, package_path, source_repo, dest_repo):
    dest_path = dest_repo / package_path.relative_to(source_repo)
    shutil.copytree(str(package_path), str(dest_path))

    with (package_path / 'resource.json').open() as source_file, \
            (dest_path / 'resource.json').open('w') as dest_file:
        resource = json.load(source_file)

        # Change the root for images (ignore screenshots)
        if 'images' in resource:
            resource["images"] = {
                n: urllib.parse.urljoin(
                    HTTP_ROOT, str(pathlib.PurePath(
                        package, "images", pathlib.Path(uri).name)))
                for n,uri in resource.get("images", {}).items() if 'icon' in n}

        # Change the root for asset uris.
        if 'assets' in resource:
            resource["assets"]["uris"] = {
                n: urllib.parse.urljoin(
                    HTTP_ROOT, str(pathlib.PurePath(
                        package, "uris", pathlib.Path(uri).name)))
                for n, uri in resource["assets"].get("uris", {}).items()}

        # Add the local docker repo prefix.
        if 'container' in resource["assets"]:
            resource["assets"]["container"]["docker"] = {
                n: format_image_name(DOCKER_ROOT, image_name)
                for n, image_name in resource["assets"]["container"].get(
                    "docker", {}).items() }

        json.dump(resource, dest_file, indent=4)

    command_path = (package_path / 'command.json')
    if not command_path.exists():
        return

    with command_path.open() as source_file, \
            (dest_path / 'command.json').open('w') as dest_file:
        command = json.load(source_file)

        command['pip'] = [
            urllib.parse.urljoin(
                HTTP_ROOT, str(pathlib.PurePath(
                    package, "commands", pathlib.Path(uri).name)))
            for uri in command.get("pip", [])
        ]
        json.dump(command, dest_file, indent=4)

if __name__ == '__main__':
    sys.exit(main())