pipeline {
  agent {
    docker {
        image 'docker:24.0.5'
        args '-v /var/run/docker.sock:/var/run/docker.sock'
    }
}

  options {
    timestamps()
  }

  tools {
    nodejs "NodeJS"
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
                
                docker build -t $DOCKER_USER/my-app:latest .
            '''
            }
        }
}

    stage('Run API for testing') {
      steps {
        sh '''
            docker images
        '''
      }
    }
  }
}