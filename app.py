# app.py
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from scheduler import Scheduler
from models import db, User, Deployment, Cluster

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
auth = HTTPBasicAuth()
scheduler = Scheduler()

# --- Authentication ---
@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.verify_password(password):
        g.current_user = user
        return True
    return False

# --- Cluster Management ---
@app.route('/cluster', methods=['POST'])
@auth.login_required
def create_cluster():
    """
    Creates a new cluster for the user's organization.
    Expects:
        name (str): The name of the cluster.
        total_ram (int): Total RAM capacity.
        total_cpu (int): Total CPU capacity.
        total_gpu (int): Total GPU capacity.
    Returns:
        (JSON): A success message with the cluster ID, or an error message.
    """
    user = g.current_user
    if not user.organization_id:
        return jsonify({'message': 'User not associated with an organization!'}), 400

    data = request.get_json()
    new_cluster = Cluster(
        name=data['name'],
        total_ram=data['total_ram'],
        total_cpu=data['total_cpu'],
        total_gpu=data['total_gpu'],
        available_ram=data['total_ram'],
        available_cpu=data['total_cpu'],
        available_gpu=data['total_gpu'],
        organization_id=user.organization_id
    )
    db.session.add(new_cluster)
    db.session.commit()

    return jsonify({'message': 'Cluster created!', 'cluster_id': new_cluster.id}), 201


@app.route('/clusters', methods=['GET'])
@auth.login_required
def get_clusters():
    """
    Retrieves all clusters belonging to the user's organization.
    Returns:
        (JSON): A list of cluster details, or an error message.
    """
    user = g.current_user
    if not user.organization_id:
        return jsonify({'message': 'User not associated with an organization!'}), 400

    clusters = Cluster.query.filter_by(organization_id=user.organization_id).all()
    cluster_list = [
        {
            'id': cluster.id,
            'name': cluster.name,
            'total_ram': cluster.total_ram,
            'total_cpu': cluster.total_cpu,
            'total_gpu': cluster.total_gpu,
            'available_ram': cluster.available_ram,
            'available_cpu': cluster.available_cpu,
            'available_gpu': cluster.available_gpu
        }
        for cluster in clusters
    ]
    return jsonify({'clusters': cluster_list}), 200

# --- Deployment Management ---
@app.route('/deployment', methods=['POST'])
@auth.login_required
def create_deployment():
    """
    Creates a new deployment and adds it to the queue.
    Expects:
        name (str): The name of the deployment.
        cluster_id (int): The ID of the target cluster.
        docker_image (str): The Docker image path.
        required_ram (int): RAM required for the deployment.
        required_cpu (int): CPU required for the deployment.
        required_gpu (int): GPU required for the deployment.
        priority (int, optional): Priority of the deployment (1-5).
    Returns:
        (JSON): A success message with the deployment ID, or an error message.
    """
    data = request.get_json()
    user = g.current_user
    new_deployment = Deployment(
        name=data['name'],
        user_id=user.id,
        cluster_id=data['cluster_id'],
        docker_image=data['docker_image'],
        required_ram=data['required_ram'],
        required_cpu=data['required_cpu'],
        required_gpu=data['required_gpu'],
        priority=data.get('priority', 1)  # Default priority is 1
    )
    db.session.add(new_deployment)
    db.session.commit()

    # Enqueue the deployment for scheduling
    scheduler.enqueue_deployment(new_deployment.id)

    # Trigger the scheduler (ideally, this should be a background task)
    scheduler.schedule_deployments()

    return jsonify({'message': 'Deployment created and queued!', 'deployment_id': new_deployment.id}), 201


@app.route('/deployments', methods=['GET'])
@auth.login_required
def get_deployments():
    """
    Retrieves all deployments associated with the user.
    Returns:
        (JSON): A list of deployment details, or an error message.
    """
    user = g.current_user
    deployments = Deployment.query.filter_by(user_id=user.id).all()
    deployment_list = [
        {
            'id': deployment.id,
            'name': deployment.name,
            'cluster_id': deployment.cluster_id,
            'docker_image': deployment.docker_image,
            'required_ram': deployment.required_ram,
            'required_cpu': deployment.required_cpu,
            'required_gpu': deployment.required_gpu,
            'status': deployment.status,
            'priority': deployment.priority,
            'created_at': deployment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for deployment in deployments
    ]
    return jsonify({'deployments': deployment_list}), 200


# --- Deployment Status Update (for internal/testing purposes) ---
@app.route('/deployment/<int:deployment_id>/status', methods=['PUT'])
def update_deployment_status(deployment_id):
    """
    Updates the status of a deployment (for testing or internal use).
    Expects:
        status (str): The new status of the deployment.
    Returns:
        (JSON): A success message, or an error message.
    """
    data = request.get_json()
    deployment = Deployment.query.get(deployment_id)
    if not deployment:
        return jsonify({'message': 'Deployment not found!'}), 404

    deployment.status = data['status']
    db.session.commit()

    return jsonify({'message': 'Deployment status updated!', 'deployment_id': deployment.id}), 200


if __name__ == '__main__':
    app.run(debug=True)
