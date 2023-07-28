# Konfigmapedit

Edit multi-file Kubernetes configmaps by downloading them into a folder, let you edit in a shell and uploads them.

## k9s plugin

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
