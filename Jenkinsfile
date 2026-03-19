pipeline {
  agent any

  options {
    timestamps()
  }

  tools {
    nodejs "NodeJS"
  }

    environment {
        PORT = credentials('PORT')
        MONGO_URI = credentials('MONGO_URI')
        DOCKER_USER = credentials('DOCKER_USER')
    }

  stages {

    stage('Pre-clean') {
      steps {
        cleanWs()
      }
    }

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install Node Dependencies') {
      steps {
        sh 'npm install'
      }
    }

    stage('Install Python Dependencies') {
        steps {
            sh '''
            python3 -m venv venv
            . venv/bin/activate
            pip install -r requirements.txt
            '''
        }
}
    stage('Build & Push Docker Image') {
        steps {
            withCredentials([usernamePassword(
            credentialsId: 'docker-hub-cred',
            usernameVariable: 'DOCKER_USER',
            passwordVariable: 'DOCKER_PASS'
            )]) {
            sh '''
                echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin
                
                docker build -t $DOCKER_USER/user-app:latest .
            '''
            }
        }
}

    stage('Run API for testing') {
      steps {
        sh 'docker run -d -p $PORT:$PORT --env PORT=$PORT --env MONGO_URI=$MONGO_URI --name users-container $DOCKER_USER/user-app:latest'
      }
    }

    stage('wait for container to start') {
        steps {
            sh 'sleep 10'
        }
    }
    stage('Start Testing') {
        steps {
            sh 'pytest allTest.py -v'
        }
    }
  }
}