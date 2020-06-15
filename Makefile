# user variables
# ==============================================================================
PACKAGE_NAME		:= building-controls-simulator
VERSION_TAG			:= 0.1.1
DOCKER_IMAGE 		:= ${PACKAGE_NAME}
LOCAL_MNT_DIR 		:= ${PWD}
DOCKER_HOME_DIR		:= /home/bcs
DOCKER_LIB_DIR		:= ${DOCKER_HOME_DIR}/lib
DOCKER_MNT_DIR		:= ${DOCKER_LIB_DIR}/${PACKAGE_NAME}
DOCKER_CREDS_DIR	:= ${DOCKER_HOME_DIR}/.config/application_default_credentials.json
# ==============================================================================

.DEFAULT_GOAL := help

docker-build: ## build docker container from Dockerfile and tag with {VERSION_TAG}.
	docker build ${LOCAL_MNT_DIR} -t ${DOCKER_IMAGE}:${VERSION_TAG}

run: ## run container {DOCKER_IMAGE}:{VERSION_TAG} in interactive mode with bash, mount volumes, open port 8888 to local host for jupyter server
	@echo "mounting: ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw"
	docker run -it \
		--name ${DOCKER_IMAGE}_v${VERSION_TAG} \
		-v ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw \
		-p 127.0.0.1:8888:8888 \
		${DOCKER_IMAGE}:${VERSION_TAG} \
		sh -c "bash"

start: ## start recently ran container by name "{DOCKER_IMAGE}_v{VERSION_TAG}"
	docker start -i ${DOCKER_IMAGE}_v${VERSION_TAG}

copy-creds: ## copy GCP credentials into docker container
	docker cp ${GOOGLE_APPLICATION_CREDENTIALS} ${DOCKER_IMAGE}_v${VERSION_TAG}:${DOCKER_CREDS_DIR}

remove-all: ## removes all exited containers
	docker ps -a -q | xargs docker rm

help: ## Show this help message.
	@echo "================================================================================"
	@echo "Building Controls Simulator" 
	@echo "make commands"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
