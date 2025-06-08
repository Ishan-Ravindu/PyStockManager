# Python, Node.js & MariaDB Development Environment

This project provides a complete development environment using VS Code Dev Containers with Python, Node.js, and MariaDB.

## Prerequisites

Before getting started, ensure you have the following installed on your machine:

- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
  - Download from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
- **Visual Studio Code**
  - Download from [https://code.visualstudio.com/](https://code.visualstudio.com/)
- **Dev Containers extension** for VS Code
  - Install from VS Code Extensions marketplace or [here](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Getting Started

### 1. Clone or Create Your Project

```bash
git clone <your-repository-url>
cd <your-project-directory>
```

Or create a new project directory:

```bash
mkdir my-project
cd my-project
```

### 2. Set Up the Dev Container Files

Ensure your project has the following structure:

```
your-project/
├── .devcontainer/
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   └── Dockerfile
├── ... (your project files)
```

### 3. Open in VS Code

1. Open VS Code
2. Open your project folder (`File > Open Folder...`)
3. When prompted, click "Reopen in Container" or:
   - Press `F1` or `Ctrl+Shift+P` (Windows/Linux) / `Cmd+Shift+P` (Mac)
   - Type and select "Dev Containers: Reopen in Container"

VS Code will build the Docker containers and set up your development environment. This may take a few minutes on the first run.

## Environment Details

### Services

The development environment includes:

- **Application Container**
  - Python 3.11
  - Node.js 20.x (latest LTS)
  - npm (latest version)
  - Common development tools

- **MariaDB Database**
  - Version: 10.11
  - Port: 3306
  - Database name: `devdb`
  - Username: `devuser`
  - Password: `devpassword`
  - Root password: `rootpassword`

### Ports

- **3306**: MariaDB database
- **3000**: Node.js application (when running)

## Working with the Environment

### Python Development

The container includes Python 3.11 with common linting and formatting tools:

```bash
# Run Python scripts
python your_script.py

# Install Python packages
pip install package-name

# Or use requirements.txt
pip install -r requirements.txt
```

Available Python tools:
- autopep8
- black
- yapf
- bandit
- flake8
- mypy
- pycodestyle
- pydocstyle
- pylint

### Node.js Development

```bash
# Check Node.js version
node --version

# Initialize a new Node.js project
npm init

# Install dependencies
npm install package-name

# Run Node.js applications
node app.js

# Or use npm scripts
npm start
```

### Database Connection

Connect to MariaDB from your applications using:

- **Host**: `db` (from within containers) or `localhost` (from host machine)
- **Port**: `3306`
- **Database**: `devdb`
- **Username**: `devuser`
- **Password**: `devpassword`

Example Python connection:

```python
import mysql.connector

connection = mysql.connector.connect(
    host="db",
    port=3306,
    database="devdb",
    user="devuser",
    password="devpassword"
)
```

Example Node.js connection:

```javascript
const mysql = require('mysql2');

const connection = mysql.createConnection({
    host: 'db',
    port: 3306,
    database: 'devdb',
    user: 'devuser',
    password: 'devpassword'
});
```

### Using MySQL Client

Access the database directly:

```bash
# Connect to MariaDB as devuser
mysql -h db -u devuser -pdevpassword devdb

# Connect as root
mysql -h db -u root -prootpassword
```

## VS Code Extensions

The following extensions are automatically installed in the container:

- ESLint
- Prettier
- Python
- Pylance

## Troubleshooting

### Container Won't Start

1. Ensure Docker is running
2. Check Docker logs: `docker-compose -f .devcontainer/docker-compose.yml logs`
3. Try rebuilding: In VS Code, run "Dev Containers: Rebuild Container"

### Database Connection Issues

1. Wait for the database to fully initialize (check logs)
2. Verify credentials match those in docker-compose.yml
3. Ensure you're using `db` as the hostname when connecting from the app container

### Port Already in Use

If ports 3306 or 3000 are already in use on your host:

1. Stop any local MySQL/MariaDB or Node.js services
2. Or modify the port mappings in docker-compose.yml

### Permission Issues

The container runs as the `vscode` user. If you encounter permission issues:

```bash
# Switch to root temporarily
sudo command-here

# Or change file ownership
sudo chown vscode:vscode file-or-directory
```

## Customization

### Adding Dependencies

#### Python Packages

Create a `requirements.txt` file in your project root:

```txt
flask==2.3.0
django==4.2.0
requests==2.31.0
```

Then install in the container:

```bash
pip install -r requirements.txt
```

#### Node.js Packages

Create a `package.json` file or install directly:

```bash
npm install express mongoose dotenv
```

### Modifying the Environment

To add system packages or tools, modify `.devcontainer/Dockerfile`:

```dockerfile
# Add this after the existing RUN command
RUN apt-get update && apt-get install -y \
    your-package-here \
    && rm -rf /var/lib/apt/lists/*
```

Then rebuild the container in VS Code.

## Data Persistence

- **MariaDB data** is persisted in a Docker volume named `mariadb-data`
- **Node modules** are stored in a separate volume for better performance
- **Your code** is mounted from your local machine and changes are reflected immediately

## Cleaning Up

To remove the containers and volumes:

```bash
# Stop and remove containers
docker-compose -f .devcontainer/docker-compose.yml down

# Remove volumes (this will delete database data!)
docker-compose -f .devcontainer/docker-compose.yml down -v
```

## Additional Resources

- [VS Code Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Python Documentation](https://docs.python.org/3.11/)
- [Node.js Documentation](https://nodejs.org/docs/)
- [MariaDB Documentation](https://mariadb.com/kb/en/documentation/)

## Support

If you encounter issues not covered in this README:

1. Check the [VS Code Dev Containers troubleshooting guide](https://code.visualstudio.com/docs/devcontainers/troubleshooting)
2. Review Docker logs for specific error messages
3. Ensure all prerequisites are properly installed and up to date