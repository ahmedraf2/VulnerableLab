# VulnerableLab

A marketplace web app for our cloud security project. Deploy it locally and use the scanner to find vulnerabilities.

## Prerequisites
python , Docker , kubectl and a local cluster (minikube or k3s pick one)

## Setup

### Verify everything works :

```bash
python3 --version
docker --version
minikube version
kubectl get nodes # minikube node should be ready (after installing minikube)
``` 
### minikube

this makes docker build inside minikube's docker , so the image is available to k8s

```bash
eval $(minikube docker-env)
docker build -t marketplace:latest .
```
 
### Deloy to kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
```
This creates the namespace , deployment , service and RBAC binding.
```bash
kubectl get pods -n marketplace -w
```
Wait until pods show `Running` and `1/1` ready

### Access the app

Port Forward
```bash
kubectl port-forward svc/marketplace-svc 5000:5000 -n marketplace
```
Then open **http://localhost:5000/** in your browser.

## Pages

- `/` - home, product listing
- `/login` `/register` `/logout` - auth
- `/products` - browse + search
- `/product/<id>` - detail + reviews
- `/dashboard` - user dashboard
- `/user/<id>` - profiles
- `/settings` - edit profile
- `/messages` - send messages
- `/transfer` - transfer money
- `/buy/<id>` - purchase
- `/order/<id>` - order detail
- `/seller/preview-banner` - banner preview tool
- `/api/check-image?url=` - image url checker
- `/internal/admin-stats` - internal stats (not linked in UI)

## Scanner

Still Not Ready