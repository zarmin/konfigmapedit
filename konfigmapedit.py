#!/usr/bin/env python3

import argparse
from kubernetes import client, config
from tempfile import TemporaryDirectory
import subprocess
import os
import difflib

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Edit multi-file Kubernetes configmaps by downloading them into a folder, let you edit and uploads them.')
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

def main():
    args = parse_args()

    config.load_kube_config()

    v1 = client.CoreV1Api()
    configmap = v1.read_namespaced_config_map(args.configmap, args.namespace)

    orginal_configmap_data = configmap.data.copy()
    
    with TemporaryDirectory(prefix='konfigmapedit-') as tempdir:
        # write configmap data to tempdir        
        for entry_name, entry_data in orginal_configmap_data.items():
            with open(tempdir + '/' + entry_name, 'w') as f:
                f.write(entry_data)
            
        # open an interactive shell in the tempdir
        current_shell = get_current_shell()
        subprocess.run([current_shell], cwd=tempdir)
        
        # read configmap data from tempdir
        configmap.data.clear()
        for entry in os.listdir(tempdir):
            if entry.startswith('.'):
                continue
            with open(tempdir + '/' + entry, 'r') as f:                
                configmap.data[entry] = f.read()

        # check if configmap data has changed
        is_changed = diff_changes(configmap.data, orginal_configmap_data)
        if not is_changed:
            print("No changes detected")
            return
        
        # handle immutable config maps
        should_replace = args.recreate
        if configmap.immutable and not args.recreate:
            print("Configmap is immutable, will replace it instead of patching it")
            should_replace = True
        
        # prompt user to upload changes
        upload_mode = "delete & create" if should_replace else "patch"
        print(f"Configmap '{configmap.metadata.name}' in namespace '{configmap.metadata.namespace}' will be updated with '{upload_mode}'")
        answer = input("Upload changes? [y/n] ")
        if answer != 'y':
            print("Aborting")
            return
        
        if should_replace:
            v1.delete_namespaced_config_map(args.configmap, args.namespace)

            # clear everything except the name
            configmap.metadata.resource_version = None
            v1.create_namespaced_config_map(args.namespace, configmap)
        else:
            v1.replace_namespaced_config_map(args.configmap, args.namespace, configmap)

if __name__ == "__main__":
    main()