pipeline {
    agent any

    environment {
        AWS_REGION        = 'us-east-1'
        AWS_ACCOUNT_ID    = credentials('AWS_ACCOUNT_ID')
        ECR_REGISTRY      = "${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
        FRONTEND_IMAGE    = "${ECR_REGISTRY}/zestora/frontend"
        BACKEND_IMAGE     = "${ECR_REGISTRY}/zestora/backend"
        IMAGE_TAG         = "${BUILD_NUMBER}"
        EC2_HOST          = credentials('EC2_HOST')
        EC2_USER          = 'ubuntu'
        SSH_KEY_CRED_ID   = 'ec2-ssh-key'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        ansiColor('xterm')
    }

    stages {
        stage('1. Checkout SCM') {
            steps {
                echo '📦 Checking out latest code from Git repository...'
                checkout scm
            }
        }

        stage('2. Code Quality & Automated Tests') {
            parallel {
                stage('Backend Unit Tests') {
                    steps {
                        echo '🐍 Running Python 3.12 Flask Unit & Integration Tests...'
                        sh '''
                            cd backend
                            python3 -m unittest test_app.py
                        '''
                    }
                }
                stage('Frontend TypeScript Build') {
                    steps {
                        echo '⚛️ Typechecking and building React SPA with Vite...'
                        sh '''
                            cd frontend
                            npm ci
                            npm run build
                        '''
                    }
                }
            }
        }

        stage('3. DevSecOps - Trivy Vulnerability Scan') {
            steps {
                echo '🛡️ Running Aqua Security Trivy Scanner on Codebase and Dockerfiles...'
                sh '''
                    trivy fs --scanners vuln,secret,config --severity HIGH,CRITICAL --exit-code 0 .
                '''
            }
        }

        stage('4. Docker Multi-Stage Image Build') {
            steps {
                echo '🐳 Building production Docker images for Frontend & Backend...'
                sh """
                    docker build -t ${BACKEND_IMAGE}:${IMAGE_TAG} -t ${BACKEND_IMAGE}:latest ./backend
                    docker build -t ${FRONTEND_IMAGE}:${IMAGE_TAG} -t ${FRONTEND_IMAGE}:latest ./frontend
                """
            }
        }

        stage('5. Trivy Container Image Scan') {
            steps {
                echo '🛡️ Scanning newly built Docker images for CVEs...'
                sh """
                    trivy image --severity CRITICAL --exit-code 0 ${BACKEND_IMAGE}:${IMAGE_TAG}
                    trivy image --severity CRITICAL --exit-code 0 ${FRONTEND_IMAGE}:${IMAGE_TAG}
                """
            }
        }

        stage('6. Push Images to AWS ECR') {
            steps {
                echo '☁️ Authenticating to Amazon ECR and pushing container images...'
                withAWS(region: "${AWS_REGION}", credentials: 'aws-jenkins-credentials') {
                    sh """
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        docker push ${BACKEND_IMAGE}:${IMAGE_TAG}
                        docker push ${BACKEND_IMAGE}:latest
                        docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                        docker push ${FRONTEND_IMAGE}:latest
                    """
                }
            }
        }

        stage('7. Terraform Infrastructure Validation') {
            steps {
                echo '🏗️ Running Terraform Format, Validation, and Plan...'
                dir('terraform') {
                    sh '''
                        terraform init -backend=false
                        terraform fmt -check || true
                        terraform validate
                    '''
                }
            }
        }

        stage('8. Deploy to AWS EC2 & Smoke Test') {
            steps {
                echo '🚀 Deploying updated containers to AWS EC2 over SSH...'
                sshagent([SSH_KEY_CRED_ID]) {
                    sh """
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} '
                            cd /home/ubuntu/app
                            sudo docker compose -f docker-compose.prod.yml pull || true
                            sudo docker compose -f docker-compose.prod.yml up -d --build
                        '
                    """
                }

                echo '🩺 Running live HTTP health checks on deployed application...'
                sh """
                    curl -f --retry 5 --retry-delay 3 http://${EC2_HOST}/healthz
                    curl -f --retry 5 --retry-delay 3 http://${EC2_HOST}/api/health
                """
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            echo '🎉 Zestora CI/CD Pipeline completed successfully! Application is LIVE.'
        }
        failure {
            echo '❌ Pipeline failed! Check logs above for errors.'
        }
    }
}
