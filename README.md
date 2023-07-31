# Konfigmapedit

Edit multi-file Kubernetes configmaps by downloading them into a folder, let you edit in a shell and uploads them.

## Installation

You can install the Konfigmapedit from PyPi:

```
pip install konfigmapedit
```

The konfigmapedit is supported on Python 3.6 and above on Linux/MacOS.

## How to use

```
# This creates a temp dir on a local machine and downloads a kubernetes configmap into it and invokes a shell in the temp dir.
# The -n flag is the namespace and the configmap1 is the name of the configmap.
$ konfigmapedit -n app1 configmap1
configmap/configmap1 in namespace app1:
You are now in an interactive shell. Edit the configmap files and exit the shell to upload the changes.
$ konfigmapedit-g6r00xk9
# here you can use shell commands, like ls, vim, nano, etc. or just open it in any editor.
# after you finished the editing you can exit the shell (ctrl+D or exit command) and the konfigmapedit will display the changes and if you accept them it will upload the changes.
```

## k9s plugin

You can use it as a k9s plugin too, where Ctrl-F on configmaps will invoke this tool.

Install instructions: https://k9scli.io/topics/plugins/

```yaml
plugin:
  editConfigMap:
    shortCut: Ctrl-F
    description: Edit as files
    scopes:
    - cm
    command: konfigmapedit
    background: false
    args:
    - '-n'
    - $NAMESPACE
    - $NAME
```
