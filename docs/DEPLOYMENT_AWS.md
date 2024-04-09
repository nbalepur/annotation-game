# AWS Deployment

Deployment instructions using Docker on AWS.

## Deploy on EC2

### Configure EC2 instance

  - Launch Amazon Linux instance of your choosing
  - Add HTTP to Inbound Security Rules with CIDR block `0.0.0.0/0`

### Install Git, Docker, and Docker Compose ([Directions](https://gist.github.com/npearce/6f3c7826c7499587f00957fee62f8ee9))

    sudo yum update -y

    sudo yum install git docker -y
    sudo service docker start
	
    \# Installs the latest version of docker-compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
    


### Set up repository

Clone repository:

    git clone https://github.com/jasmaa/kuiperbowl.git

Configure `.env` with proper credentials.

### Set up database

Start application:

    sudo docker-compose up --build -d

Get a shell into running web process:

    sudo docker exec -it kuiperbowl_web_1 bash

Bootstrap database within the container:

    # Download and convert Protobowl question dumps
    python ./scripts/pb_load.py

    # Bootstrap database
    python manage.py migrate
    python manage.py loaddata fixtures/default_rooms.json
    python manage.py loaddata fixtures/pbdump.json # This will take a while

Exit container and shutdown application:

    exit
    sudo docker-compose down

### Launch application

    sudo docker-compose up --build -d


## Set Up Networking

### Create Load Balancer

- Create an Application Load Balancer

- Configure Load Balancer
  - Add HTTP and HTTPS to Listeners.

- Configure Security Groups
  - Create/Add security group with inbound rules allowing all IPv4 and IPv6.
    - `80`, `0.0.0.0/0`
    - `80`, `::/0`
    - `443`, `0.0.0.0/0`
    - `443`, `::/0`

- Register Targets
  - Create target group listening on the previously set up EC2 instance.

### Set Up DNS with Route 53

- Add an `A` record pointing the domain name to the load balancer in the domain's hosted zone.