<#
.SYNOPSIS
Initializes the Keycloak database inside the running ETL postgres container.

.DESCRIPTION
This PowerShell script connects to the running Docker container `etl-age_db-1` via `docker exec`
and runs the necessary PostgreSQL commands to create the `keycloak` role and database.
It is designed to cleanly handle cases where the database or user already exists.

.EXAMPLE
.\init_keycloak.ps1
#>

$ContainerName = "aml-age-db"

# Check if the container is running
$ContainerStatus = (docker inspect -f '{{.State.Status}}' $ContainerName 2>$null)
if ($ContainerStatus -ne "running") {
    Write-Host "Error: Container '$ContainerName' is not running." -ForegroundColor Red
    exit 1
}

Write-Host "Container '$ContainerName' is running. Initializing Keycloak database..." -ForegroundColor Yellow

# Use a single SQL string safely passed to psql inside the container
$SqlCommands = "
\set ON_ERROR_STOP 0
CREATE ROLE keycloak LOGIN PASSWORD 'keycloak';
CREATE DATABASE keycloak OWNER keycloak;
\set ON_ERROR_STOP 1
"

# Execute the command inside docker by passing it as standard input
Write-Host "Executing SQL inside Docker..." -ForegroundColor Cyan
$SqlCommands | docker exec -i $ContainerName psql -U postgres

Write-Host "Keycloak Database initialization complete." -ForegroundColor Green
exit 0
