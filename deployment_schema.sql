-- deployment_schema.sql

-- Drop existing tables if they exist
DROP TABLE IF EXISTS deployments;
DROP TABLE IF EXISTS organization_invites;
DROP TABLE IF EXISTS clusters;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS organizations;

-- Create `users` table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    organization_id INTEGER,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

-- Create `organizations` table
CREATE TABLE organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Create `clusters` table
CREATE TABLE clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    total_ram INTEGER NOT NULL,
    total_cpu INTEGER NOT NULL,
    total_gpu INTEGER NOT NULL,
    available_ram INTEGER NOT NULL,
    available_cpu INTEGER NOT NULL,
    available_gpu INTEGER NOT NULL,
    organization_id INTEGER NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

-- Create `deployments` table
CREATE TABLE deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    docker_image TEXT NOT NULL,
    required_ram INTEGER NOT NULL,
    required_cpu INTEGER NOT NULL,
    required_gpu INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (cluster_id) REFERENCES clusters(id)
);

-- Create `organization_invites` table
CREATE TABLE organization_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    code TEXT UNIQUE NOT NULL,
    used BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);
