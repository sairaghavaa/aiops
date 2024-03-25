pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git 'https://gitlab.com/your-repo.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t your-image .'
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerHubCredentials', passwordVariable: 'DOCKER_HUB_PASSWORD', usernameVariable: 'DOCKER_HUB_USERNAME')]) {
                    sh 'docker login -u $DOCKER_HUB_USERNAME -p $DOCKER_HUB_PASSWORD'
                    sh 'docker push your-image'
                }
            }
        }

        stage('Deploy to ECS') {
            steps {
                withCredentials([string(credentialsId: 'awsCredentials', variable: 'AWS_CREDENTIALS')]) {
                    sh 'aws ecs update-service --cluster your-cluster --service your-service --force-new-deployment'
                }
            }
        }
    }
}