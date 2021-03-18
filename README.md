# Automation

- https://selenium-python.readthedocs.io/
- https://www.crummy.com/software/BeautifulSoup/bs4/doc/#searching-the-tree
- https://hub.docker.com/u/ibmfunctions
- https://jamesthom.as/2017/08/large-applications-on-openwhisk/
- https://cloud.ibm.com/docs/openwhisk?topic=openwhisk-prep#prep_python_docker

To execute `kubectl commands to my cluster`:
```bash
ibmcloud ks cluster config --cluster bp2vucbw0acqse0v8p9g
```
To list containers:
```bash
docker ps
kubectl get pods
```
To execute a command:
```bash
docker exec 7b45e81dcc93 ls
kubectl exec appen-deployment-6855d7d88f-9r5ns ls screen_caps
```
To copy a file:
```bash
docker cp 7b45e81dcc93:/app/screen_caps/1596825388.148049.png 1596825388.148049.png
```

To exec into a container:
```bash
docker exec -it 7b45e81dcc93 /bin/bash
```
