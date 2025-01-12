# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class User(db.Model):
  __tablename__ = 'users'
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String, unique=True, nullable=False)
  password = db.Column(db.String, nullable=False)
  organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
  
  organization = relationship("Organization", back_populates="users")
  
class Organization(db.Model):
  __tablename__ = 'organizations'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, unique=True, nullable=False)
  
  users = relationship("User", back_populates="organization")
  clusters = relationship("Cluster", back_populates="organization")
  invites = relationship("OrganizationInvite", back_populates="organization")
  
class Cluster(db.Model):
  __tablename__ = 'clusters'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, unique=True, nullable=False)
  total_ram = db.Column(db.Integer, nullable=False)
  total_cpu = db.Column(db.Integer, nullable=False)
  total_gpu = db.Column(db.Integer, nullable=False)
  available_ram = db.Column(db.Integer, nullable=False)
  available_cpu = db.Column(db.Integer, nullable=False)
  available_gpu = db.Column(db.Integer, nullable=False)
  organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
  
  organization = relationship("Organization", back_populates="clusters")
  
class Deployment(db.Model):
  __tablename__ = 'deployments'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, nullable=False)
  user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
  cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'), nullable=False)
  docker_image = db.Column(db.String, nullable=False)
  required_ram = db.Column(db.Integer, nullable=False)
  required_cpu = db.Column(db.Integer, nullable=False)
  required_gpu = db.Column(db.Integer, nullable=False)
  status = db.Column(db.String, nullable=False, default='queued')
  priority = db.Column(db.Integer, nullable=False, default=1)
  created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
  
  user = relationship("User")
  cluster = relationship("Cluster")
  
class OrganizationInvite(db.Model):
  __tablename__ = 'organization_invites'
  id = db.Column(db.Integer, primary_key=True)
  organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
  code = db.Column(db.String, unique=True, nullable=False)
  used = db.Column(db.Boolean, default=False, nullable=False)
  
  organization = relationship("Organization", back_populates="invites")
