pipeline {
  agent any

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

    stage('Install Dependencies') {
      steps {
        sh 'npm install'
      }
    }
    stage('Install python dependencies'){
      steps {
        sh 'python3 --version'
        }
  }
  }
}
