import pytest
import json
from app import app, db
from models import User, Organization, Cluster, Deployment, OrganizationInvite


@pytest.fixture
def client():
    """Fixture to set up the test client and database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


def register_user(client, username, password):
    """Helper function to register a user."""
    return client.post('/register', json={'username': username, 'password': password})


def authenticate_user(username, password):
    """Helper function to generate Basic Auth header."""
    auth_str = f"{username}:{password}"
    return {'Authorization': 'Basic ' + auth_str.encode('utf-8').decode('utf-8')}


def test_register_and_login(client):
    # Test user registration
    register_data = {'username': 'testuser', 'password': 'testpassword'}
    response = register_user(client, **register_data)
    assert response.status_code == 201

    # Test login with valid credentials
    response = client.post('/login', json=register_data, headers=authenticate_user(**register_data))
    assert response.status_code == 200


def test_create_and_join_organization(client):
    # Register a user
    register_user(client, 'orguser', 'testpassword')

    # Test organization creation
    response = client.post('/organization', json={'name': 'TestOrg'},
                           headers=authenticate_user('orguser', 'testpassword'))
    assert response.status_code == 201
    invite_code = json.loads(response.data)['invite_code']

    # Register another user and join the organization
    register_user(client, 'joinuser', 'testpassword')
    response = client.post(f'/join/{invite_code}', headers=authenticate_user('joinuser', 'testpassword'))
    assert response.status_code == 200


def test_create_cluster(client):
    # Register a user and create an organization
    register_user(client, 'clusteruser', 'testpassword')
    response = client.post('/organization', json={'name': 'ClusterOrg'},
                           headers=authenticate_user('clusteruser', 'testpassword'))
    invite_code = json.loads(response.data)['invite_code']

    # Join the organization
    client.post(f'/join/{invite_code}', headers=authenticate_user('clusteruser', 'testpassword'))

    # Test cluster creation
    cluster_data = {'name': 'TestCluster', 'total_ram': 16, 'total_cpu': 4, 'total_gpu': 2}
    response = client.post('/cluster', json=cluster_data, headers=authenticate_user('clusteruser', 'testpassword'))
    assert response.status_code == 201


def test_create_deployment(client):
    # Setup: Register user, create org, create cluster
    register_user(client, 'deployuser', 'testpassword')
    response = client.post('/organization', json={'name': 'DeployOrg'},
                           headers=authenticate_user('deployuser', 'testpassword'))
    invite_code = json.loads(response.data)['invite_code']

    client.post(f'/join/{invite_code}', headers=authenticate_user('deployuser', 'testpassword'))
    response = client.post('/cluster', json={
        'name': 'DeployCluster', 'total_ram': 32, 'total_cpu': 8, 'total_gpu': 4},
        headers=authenticate_user('deployuser', 'testpassword'))
    cluster_id = json.loads(response.data)['cluster_id']

    # Test deployment creation
    deployment_data = {
        'name': 'TestDeployment',
        'cluster_id': cluster_id,
        'docker_image': 'nginx:latest',
        'required_ram': 4,
        'required_cpu': 1,
        'required_gpu': 0,
        'priority': 3
    }
    response = client.post('/deployment', json=deployment_data, headers=authenticate_user('deployuser', 'testpassword'))
    assert response.status_code == 201


def test_get_deployments(client):
    # Setup: Create a deployment
    test_create_deployment(client)

    # Test getting deployments
    response = client.get('/deployments', headers=authenticate_user('deployuser', 'testpassword'))
    assert response.status_code == 200

    deployments = json.loads(response.data)['deployments']
    assert len(deployments) == 1
    assert deployments[0]['name'] == 'TestDeployment'


def test_get_clusters(client):
    # Setup: Create a cluster
    test_create_cluster(client)

    # Test getting clusters
    response = client.get('/clusters', headers=authenticate_user('clusteruser', 'testpassword'))
    assert response.status_code == 200

    clusters = json.loads(response.data)['clusters']
    assert len(clusters) == 1
    assert clusters[0]['name'] == 'TestCluster'
