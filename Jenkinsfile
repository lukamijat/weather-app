pipeline {
    agent any

    enviroment {
        IMAGE_DEV = "weather-cli-dev"
        IMAGE_PROD = "weather-cli"
        REGISTRY = "ghcr.io/${env.GITHUB_REPOSITORY}"  // or docker hub
    }


options {
    timestamps()
}

stages {
    stage('Checkout') {
        steps {
            checkout scm
        }
    }

    stage('Build Dev Image') {
        steps {
            sh '''
              docker build -f docker/Dockerfile.dev -t $IMAGE_DEV .
            '''  
        }
    }

    stage('Lint & Test') {
      steps {  
        sh ''' 
          docker run --rm $IMAGE_DEV
        '''
      }
    }

    stage('Build Prod Image') {
        when { branch 'main' }
        steps {
            sh ''' 
              docker build -f docker/Dockerfile.prod -t $IMAGE_PROD .
            '''
        }
    }

    stage('Push prod image') {
        when { branch 'main' }
        steps {
            withCredentials([usernamePassword(credentialsId: 'ghcr-creds', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                sh ''' 
                  echo "$REG_PASS" | docker login ghcr.io -u "$REG_USER" --password-stdin
                  IMAGE_ID=$REGISTRY/weather-cli
                  IMAGE_ID=$(echo $IMAGE_ID | tr '[:upper:]' '[:lower:]')
                  docker tag $IMAGE_PROD $IMAGE_ID:latest
                  docker push $IMAGE_ID:latest
                '''
            }
        }
    }
}

    post {
        always {
            junit allowEmptyResults: true, testResults: 'pytest.xml'
            cleanWs()
        }
    }
}