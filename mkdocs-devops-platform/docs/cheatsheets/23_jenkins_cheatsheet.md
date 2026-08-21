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

---

## 6. Advanced Declarative Programming Features

Jenkins Declarative Pipeline offers powerful built-in directives for complex CI/CD workflows without needing heavy Groovy scripting.

### 6.1 Conditionals (`when`)
Execute a stage only if specific conditions are met.

```groovy
stage('Deploy to Prod') {
    when {
        branch 'main'
        environment name: 'DEPLOY_ENV', value: 'production'
        // Or use custom Groovy expressions
        expression { return params.EXECUTE_DEPLOY == true }
    }
    steps {
        sh './deploy.sh prod'
    }
}
```

### 6.2 Parallel Execution (`parallel`)
Run multiple stages simultaneously to speed up build times (e.g., running tests across different suites).

```groovy
stage('Parallel Testing') {
    parallel {
        stage('Unit Tests') {
            steps { sh 'make test-unit' }
        }
        stage('Integration Tests') {
            steps { sh 'make test-integration' }
        }
        stage('UI Tests') {
            steps { sh 'make test-ui' }
        }
    }
}
```

### 6.3 Manual Approvals (`input`)
Pause the pipeline and wait for human interaction before proceeding.

```groovy
stage('Approval Gate') {
    steps {
        input message: 'Approve deployment to production?', 
              ok: 'Deploy',
              submitter: 'ops-team,sre-leads'
    }
}
```

### 6.4 Pipeline Options (`options`)
Configure pipeline-specific behaviors.

```groovy
pipeline {
    agent any
    options {
        buildDiscarder(logRotator(numToKeepStr: '30')) // Keep last 30 builds
        disableConcurrentBuilds() // Prevent parallel executions of this job
        timeout(time: 1, unit: 'HOURS') // Fail the build if it takes > 1 hour
        timestamps() // Prepend logs with timestamps
    }
    stages { /* ... */ }
}
```

### 6.5 Matrix Builds (`matrix`)
Run the same stage multiple times with different variable combinations.

```groovy
stage('Test Matrix') {
    matrix {
        axes {
            axis {
                name 'OS'
                values 'linux', 'windows', 'mac'
            }
            axis {
                name 'BROWSER'
                values 'chrome', 'firefox', 'safari'
            }
        }
        excludes {
            // Safari doesn't run on Linux/Windows
            exclude {
                axis { name 'OS'; notValues 'mac' }
                axis { name 'BROWSER'; values 'safari' }
            }
        }
        stages {
            stage('Run') {
                steps {
                    echo "Testing on ${OS} with ${BROWSER}"
                }
            }
        }
    }
}
```

### 6.6 Dropping into Script (`script`)
Declarative pipelines are strict. If you need complex `if/else` loops or custom Groovy logic, wrap it in a `script` block.

```groovy
stage('Complex Logic') {
    steps {
        script {
            def servers = ['web-01', 'web-02', 'web-03']
            for (String server : servers) {
                echo "Deploying to ${server}..."
                // custom groovy logic
            }
            
            if (currentBuild.number % 2 == 0) {
                echo "Even build number!"
            }
        }
    }
}
```
