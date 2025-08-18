pipeline {
    agent any

    stages {
        stage('Install') {
            steps {
                sh 'python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt'
            }
        }
        stage('Lint') {
            steps {
                sh '. venv/bin/activate && pip install flake8 && flake8 weather'
            }
        }
        stage('Test') {
            steps {
                sh '. venv/bin/activate && pip install pytest requests-mock && pytest --maxfail=1 --disable-warnings -q'
            }
        }
        stage('Package') {
            steps {
                sh '. venv/bin/activate && python setup.py sdist bdist_wheel'
            }
        }
    }

    post {
        always {
            junit 'pytest.xml'
        }
    }
}
