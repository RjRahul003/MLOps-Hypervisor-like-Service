import redis
from models import db, Deployment, Cluster

class Scheduler:
    def __init__(self, redis_host='localhost', redis_port=6379):
        """Initializes the scheduler with a connection to Redis."""
        self.queue = redis.Redis(host=redis_host, port=redis_port, db=0)
        self.queue_name = 'deployment_queue'

    def enqueue_deployment(self, deployment_id):
        """Adds a deployment ID to the right end of the queue."""
        self.queue.rpush(self.queue_name, deployment_id)
        print(f"Deployment {deployment_id} added to the queue.")

    def dequeue_deployment(self):
        """Removes and returns the deployment ID from the left end of the queue (FIFO)."""
        deployment_id = self.queue.lpop(self.queue_name)
        if deployment_id:
            print(f"Deployment {deployment_id.decode()} removed from the queue.")
            return int(deployment_id)
        return None

    def get_queue_length(self):
        """Returns the current number of deployments in the queue."""
        length = self.queue.llen(self.queue_name)
        print(f"Current queue length: {length}")
        return length

    def schedule_deployments(self):
        """
        Implements the main scheduling logic. It checks for available resources
        and updates deployment status accordingly.
        """
        print("Scheduler is running...")
        while self.get_queue_length() > 0:
            deployment_id = self.dequeue_deployment()
            if deployment_id is None:
                continue

            with db.session.no_autoflush:
                deployment = Deployment.query.get(deployment_id)
                if not deployment:
                    print(f"Deployment {deployment_id} not found.")
                    continue

                cluster = Cluster.query.get(deployment.cluster_id)
                if not cluster:
                    print(f"Cluster for deployment {deployment_id} not found.")
                    deployment.status = 'failed'
                    db.session.commit()
                    continue

                if (cluster.available_ram >= deployment.required_ram and
                    cluster.available_cpu >= deployment.required_cpu and
                    cluster.available_gpu >= deployment.required_gpu):
                    # Allocate resources
                    print(f"Allocating resources for deployment {deployment_id} on cluster {cluster.id}")
                    cluster.available_ram -= deployment.required_ram
                    cluster.available_cpu -= deployment.required_cpu
                    cluster.available_gpu -= deployment.required_gpu
                    deployment.status = 'running'
                    db.session.commit()
                else:
                    print(f"Not enough resources for deployment {deployment_id} on cluster {cluster.id}. Requeueing...")
                    # Put it back based on priority
                    self.requeue_deployment_by_priority(deployment_id)

    def requeue_deployment_by_priority(self, deployment_id):
        """
        Re-inserts a deployment into the queue based on its priority.
        Higher priority deployments are placed ahead of lower priority ones.
        """
        deployment = Deployment.query.get(deployment_id)
        if not deployment:
            print(f"Deployment {deployment_id} not found for requeueing.")
            return

        queue_length = self.queue.llen(self.queue_name)
        print(f"Requeueing deployment {deployment_id} with priority {deployment.priority}.")

        # Temporarily store lower priority deployments
        lower_priority_deployments = []
        for _ in range(queue_length):
            queued_deployment_id = self.queue.lpop(self.queue_name)
            if queued_deployment_id is None:
                break
            queued_deployment_id = int(queued_deployment_id)
            queued_deployment = Deployment.query.get(queued_deployment_id)
            if queued_deployment and queued_deployment.priority <= deployment.priority:
                lower_priority_deployments.append(queued_deployment_id)
            else:
                # Put back higher priority deployments
                self.queue.lpush(self.queue_name, queued_deployment_id)

        # Add the current deployment
        self.queue.lpush(self.queue_name, deployment_id)

        # Add back the lower priority deployments
        for dep_id in reversed(lower_priority_deployments):
            self.queue.lpush(self.queue_name, dep_id)

        print(f"Deployment {deployment_id} requeued. Current queue: "
              f"{[self.queue.lindex(self.queue_name, i).decode() for i in range(self.queue.llen(self.queue_name))]}")
