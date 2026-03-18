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

    stage('Install Node Dependencies') {
      steps {
        sh 'npm install'
      }
    }

    stage('Install Python Dependencies') {
      steps {
        sh 'python3 --version'
        sh 'pip install -r requirements.txt'
      }
    }

  }
}