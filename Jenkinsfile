pipeline {
  agent {
    docker {
      image 'python:3.11-slim'
      // adjust or remove this mount if the path doesn't exist on your Jenkins host
      args '-v /var/jenkins_home/.cache/pip:/root/.cache/pip'
    }
  }

  environment {
    VENV = "${WORKSPACE}/.venv"
    PATH = "${env.VENV}/bin:${env.PATH}"
    PIP_CACHE_DIR = "/root/.cache/pip"
  }

  options {
    timestamps()
    timeout(time: 45, unit: 'MINUTES')
  }

  stages {
    stage('Install') {
      steps {
        sh '''
          set -euo pipefail
          python -m venv "$VENV"
          python -m pip install --upgrade pip setuptools wheel
          # Prefer installing dev extras for test/lint: either use requirements-dev.txt or pyproject extras
          if [ -f requirements-dev.txt ]; then
            python -m pip install -r requirements-dev.txt
          elif [ -f requirements.txt ]; then
            python -m pip install -r requirements.txt
          else
            python -m pip install -e ".[dev]" || true
          fi
        '''
      }
    }

    stage('Lint') {
      steps {
        sh '''
          set -euo pipefail
          # fail if linters error
          python -m flake8 weather
        '''
      }
    }

    stage('Test') {
      steps {
        sh '''
          set -euo pipefail
          # produce junit xml and coverage xml for Jenkins / Codecov
          pytest --maxfail=1 --disable-warnings -q --junitxml=pytest.xml --cov=weather --cov-report=xml
        '''
      }
    }

    stage('Package') {
      when { branch 'main' } // build artifacts on main (but do NOT publish here)
      steps {
        sh '''
          set -euo pipefail
          python -m pip install --upgrade build
          python -m build
        '''
      }
    }

    stage('Publish (tags only)') {
      // only run publish when Jenkins is building a Git tag (safe release)
      when { buildingTag() }
      steps {
        withCredentials([string(credentialsId: 'PYPI_TOKEN', variable: 'PYPI_TOKEN')]) {
          sh '''
            set -euo pipefail
            python -m pip install --upgrade twine
            # follow twine guidance for API tokens: username __token__
            python -m twine upload dist/* -u __token__ -p "$PYPI_TOKEN"
          '''
        }
      }
    }
  }

  post {
    always {
      junit allowEmptyResults: true, testResults: 'pytest.xml'
      archiveArtifacts artifacts: 'dist/**, build/**, *.whl, *.tar.gz', allowEmptyArchive: true
      archiveArtifacts artifacts: 'pytest.xml, coverage.xml', allowEmptyArchive: true
      cleanWs()
    }
    failure {
      // optionally add notifications here
    }
  }
}
