# Jenkins DevOps Cheat Sheet

## 1. Jenkins Architecture Overview
- **Controller (Master):** Schedules jobs, dispatches builds to agents, serves the UI, and stores configuration.
- **Agent (Slave):** Executes the actual build steps. Can be static (VMs) or dynamic (Kubernetes pods, Docker containers).
- **Executor:** A slot on an agent available to run a job.

---

## 2. Declarative Pipeline Syntax (Jenkinsfile)

A standard, readable way to define CI/CD as code.

```groovy
pipeline {
    agent any // or agent { docker { image 'maven:3.8.1-jdk-11' } }
    
    environment {
        DOCKER_CREDS = credentials('docker-hub-credentials')
        APP_VERSION = "1.0.${BUILD_NUMBER}"
    }
    
    parameters {
        choice(name: 'ENVIRONMENT', choices: ['dev', 'prod'], description: 'Deploy target')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build & Test') {
            steps {
                sh 'mvn clean package'
            }
            post {
                always {
                    junit 'target/surefire-reports/*.xml'
                }
            }
        }
        
        stage('Docker Image') {
            steps {
                sh 'docker build -t myapp:${APP_VERSION} .'
            }
        }
    }
    
    post {
        success {
            echo "Build successful! Version: ${APP_VERSION}"
        }
        failure {
            echo "Build failed!"
            slackSend(channel: '#builds', message: "Failed: ${env.JOB_NAME} [${env.BUILD_NUMBER}]")
        }
    }
}
```

---

## 3. Kubernetes Dynamic Agents
Using the Kubernetes Plugin to spin up ephemeral pods per build.

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-agent
spec:
  containers:
  - name: maven
    image: maven:3.8.1-jdk-11
    command:
    - cat
    tty: true
  - name: docker
    image: docker:19.03.12
    command:
    - cat
    tty: true
'''
        }
    }
    stages {
        stage('Build') {
            steps {
                container('maven') {
                    sh 'mvn --version'
                }
            }
        }
    }
}
```

---

## 4. Useful Global Variables
- `env.BUILD_NUMBER` - The current build number (e.g. 153)
- `env.JOB_NAME` - Name of the project
- `env.BRANCH_NAME` - Branch currently being built
- `env.WORKSPACE` - Absolute path to the workspace directory
- `currentBuild.result` - Status of the build (`SUCCESS`, `FAILURE`, `ABORTED`)

---

## 5. Jenkins CLI
Interact with Jenkins from the terminal using the JAR CLI:

```bash
# Download CLI
wget http://jenkins-url:8080/jnlpJars/jenkins-cli.jar

# Build a job
java -jar jenkins-cli.jar -s http://jenkins-url:8080/ -auth admin:TOKEN build my-pipeline

# Restart Jenkins
java -jar jenkins-cli.jar -s http://jenkins-url:8080/ -auth admin:TOKEN safe-restart
```
