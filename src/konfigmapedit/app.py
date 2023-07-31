#!/usr/bin/env python3

import argparse
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from tempfile import TemporaryDirectory
import subprocess
import os
import difflib

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Edit multi-file Kubernetes configmaps by downloading them into a folder, let you edit in a shell and uploads them.')
    parser.add_argument('-n', '--namespace', type=str, help='Namespace of the configmap', required=False, default='default')
    parser.add_argument('-r', '--recreate', type=bool, help='Recreate (delete & create) the configmap instead of patching it (default is patching)', required=False, default=False)
    parser.add_argument('configmap', type=str, help='Name of the configmap')
    args = parser.parse_args()
    return args

def get_current_shell() -> str:
    shell = os.environ.get('SHELL')
    if shell is None:
        shell = '/bin/sh'
    return shell

def diff_changes(new_data: dict, old_data: dict) -> bool:
    all_filenames = sorted(list(set(new_data.keys()) | set(old_data.keys())))
    diffcount = 0
    for name in all_filenames:
        if name not in old_data:
            print(f"# File '{name}' is new")
            diffcount += 1
            
        if name not in new_data:
            print(f"# File '{name}' was deleted")
            diffcount += 1

        old_entry = (old_data.get(name, '') or '').splitlines()
        new_entry = (new_data.get(name, '') or '').splitlines()
        
        if old_entry != new_entry:
            diffcount += 1
            diff_output = difflib.unified_diff(old_entry, new_entry, fromfile=name, tofile=name, lineterm='')
            print("\n".join(diff_output))
            print("")

    return diffcount > 0

def write_configmap_data_to_tempdir(configmap_data: dict, tempdir: str):
    for entry_name, entry_data in configmap_data.items():
        with open(tempdir + '/' + entry_name, 'w') as f:
            f.write(entry_data)

def read_configmap_data_from_tempdir(tempdir: str) -> dict:
    configmap_data = {}
    for entry in os.listdir(tempdir):
        if entry.startswith('.'):
            continue
        with open(tempdir + '/' + entry, 'r') as f:                
            configmap_data[entry] = f.read()
    return configmap_data

def invoke_shell(current_dir: str):
    current_shell = get_current_shell()
    subprocess.run([current_shell], cwd=current_dir)

def main():
    args = parse_args()

    config.load_kube_config()

    try:         
        v1 = client.CoreV1Api()
        configmap = v1.read_namespaced_config_map(args.configmap, args.namespace)
    except ApiException as e:
        if e.status == 404:
            print(f"Configmap '{args.configmap}' in namespace '{args.namespace}' not found")
        else:
            print(f"Kubernetes error: {e}")
        return False

    orginal_configmap_data = configmap.data.copy()
    
    with TemporaryDirectory(prefix='konfigmapedit-') as tempdir:
        write_configmap_data_to_tempdir(orginal_configmap_data, tempdir)

        while True:
            # open an interactive shell in the tempdir
            print(f"configmap/{args.configmap} in namespace {args.namespace}:")
            print("You are now in an interactive shell. Edit the configmap files and exit the shell to upload the changes.")
            invoke_shell(tempdir)
            
            # read configmap data from tempdir
            configmap.data = read_configmap_data_from_tempdir(tempdir)

            # check if configmap data has changed
            is_changed = diff_changes(configmap.data, orginal_configmap_data)
            if not is_changed:
                print("No changes detected")
                return True
            
            # handle immutable config maps
            should_replace = args.recreate
            if configmap.immutable and not args.recreate:
                print("Configmap is immutable, will replace it instead of patching it")
                should_replace = True
            
            # prompt user to upload changes
            upload_mode = "delete & create" if should_replace else "patch"
            print(f"Configmap '{configmap.metadata.name}' in namespace '{configmap.metadata.namespace}' will be updated with '{upload_mode}'")
            answer = input("Upload changes? yes / [no] / abort: ")
            # if aborted then exit
            if answer == 'abort':
                print("Aborting")
                return False
            # if no, then reopen the shell
            if answer != 'yes':
                continue
            
            # delete & create or patch configmap
            if should_replace:
                v1.delete_namespaced_config_map(args.configmap, args.namespace)

                # clear resource_version, because it is not allowed to set it when creating a resource
                configmap.metadata.resource_version = None
                v1.create_namespaced_config_map(args.namespace, configmap)
            else:
                v1.replace_namespaced_config_map(args.configmap, args.namespace, configmap)

            print("Changes uploaded")
            
            return True
