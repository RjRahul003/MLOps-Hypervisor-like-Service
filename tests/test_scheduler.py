import pytest
from scheduler import Scheduler
from models import db, Deployment, Cluster
from app import app

@pytest.fixture
def scheduler():
    """
    Fixture to initialize the Scheduler instance with a test database.
    """
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield Scheduler()

@pytest.fixture
def sample_deployment(scheduler):
    """
    Fixture to create a sample deployment and associated cluster for testing.
    """
    with app.app_context():
        cluster = Cluster(
            name="TestCluster",
            total_ram=10,
            total_cpu=4,
            total_gpu=2,
            available_ram=10,
            available_cpu=4,
            available_gpu=2,
            organization_id=1
        )
        db.session.add(cluster)
        db.session.commit()

        deployment = Deployment(
            name="TestDeployment",
            user_id=1,
            cluster_id=cluster.id,
            docker_image="testimage",
            required_ram=2,
            required_cpu=1,
            required_gpu=0,
            priority=1
        )
        db.session.add(deployment)
        db.session.commit()

        yield deployment

def test_enqueue_dequeue(scheduler, sample_deployment):
    """
    Test enqueue and dequeue operations for the scheduler.
    """
    # Test Enqueue
    scheduler.enqueue_deployment(sample_deployment.id)
    assert scheduler.get_queue_length() == 1

    # Test Dequeue
    dequeued_id = scheduler.dequeue_deployment()
    assert dequeued_id == sample_deployment.id
    assert scheduler.get_queue_length() == 0

def test_schedule_deployments_success(scheduler, sample_deployment):
    """
    Test successful deployment scheduling with resource allocation.
    """
    with app.app_context():
        scheduler.enqueue_deployment(sample_deployment.id)
        scheduler.schedule_deployments()

        # Verify deployment status and resource allocation
        updated_deployment = Deployment.query.get(sample_deployment.id)
        assert updated_deployment.status == 'running'

        cluster = Cluster.query.get(sample_deployment.cluster_id)
        assert cluster.available_ram == 8
        assert cluster.available_cpu == 3

def test_schedule_deployments_failure(scheduler):
    """
    Test deployment scheduling failure due to insufficient resources.
    """
    with app.app_context():
        cluster = Cluster.query.first()
        deployment = Deployment(
            name="ResourceHungryDeployment",
            user_id=1,
            cluster_id=cluster.id,
            docker_image="testimage",
            required_ram=12,
            required_cpu=6,
            required_gpu=4,
            priority=1
        )
        db.session.add(deployment)
        db.session.commit()

        scheduler.enqueue_deployment(deployment.id)
        scheduler.schedule_deployments()

        # Verify deployment status and unchanged resources
        updated_deployment = Deployment.query.get(deployment.id)
        assert updated_deployment.status == 'queued'

        cluster = Cluster.query.get(deployment.cluster_id)
        assert cluster.available_ram == 10

def test_requeue_deployment_by_priority(scheduler):
    """
    Test requeuing deployments by priority.
    """
    with app.app_context():
        cluster = Cluster.query.first()

        # Create deployments with different priorities
        deployment_low = Deployment(
            name="LowPriorityDeployment",
            user_id=1,
            cluster_id=cluster.id,
            docker_image="testimage",
            required_ram=2,
            required_cpu=1,
            required_gpu=0,
            priority=1
        )
        deployment_high = Deployment(
            name="HighPriorityDeployment",
            user_id=1,
            cluster_id=cluster.id,
            docker_image="testimage",
            required_ram=2,
            required_cpu=1,
            required_gpu=0,
            priority=5
        )
        db.session.add_all([deployment_low, deployment_high])
        db.session.commit()

        scheduler.enqueue_deployment(deployment_low.id)
        scheduler.enqueue_deployment(deployment_high.id)

        # Requeue deployments by priority
        scheduler.requeue_deployment_by_priority(deployment_high.id)
        scheduler.requeue_deployment_by_priority(deployment_low.id)

        # Verify higher priority deployment is dequeued first
        dequeued_id = scheduler.dequeue_deployment()
        assert dequeued_id == deployment_high.id
