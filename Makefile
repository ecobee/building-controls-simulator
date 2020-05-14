# user variables
# ==============================================================================
PACKAGE_NAME		:= building-controls-simulator
VERSION				:= 0.1.1
CONTAINER_NAME 		:= ${PACKAGE_NAME}
LOCAL_MNT_DIR 		:= ${PWD}
DOCKER_HOME_DIR		:= /home/bcs
DOCKER_LIB_DIR		:= ${DOCKER_HOME_DIR}/lib
DOCKER_MNT_DIR		:= ${DOCKER_LIB_DIR}/${PACKAGE_NAME}
DOCKER_CREDS_DIR	:= ${DOCKER_HOME_DIR}/.config/application_default_credentials.json
# ==============================================================================

.DEFAULT_GOAL := help

build-docker: ## build docker container from Dockerfile and tag with {VERSION}.
	docker build ${LOCAL_MNT_DIR} -t ${CONTAINER_NAME}:${VERSION}

run: ## run container {CONTAINER_NAME}:{VERSION} in interactive mode with bash, mount volumes, open port 8888 to local host for jupyter server
	@echo "mounting: ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw"
	docker run -it \
		--name ${CONTAINER_NAME}_v${VERSION} \
		-v ${LOCAL_MNT_DIR}:${DOCKER_MNT_DIR}:rw \
		-p 127.0.0.1:8888:8888 \
		${CONTAINER_NAME}:${VERSION} \
		sh -c "bash"

start: ## start recently ran container by name "{CONTAINER_NAME}_v{VERSION}"
	docker start -i ${CONTAINER_NAME}_v${VERSION}

copy-creds: ## copy GCP credentials into docker container
	docker cp ${GOOGLE_APPLICATION_CREDENTIALS} ${CONTAINER_NAME}_v${VERSION}:${DOCKER_CREDS_DIR}

remove-all: ## removes all exited containers
	docker ps -a -q | xargs docker rm

help: ## Show this help message.
	@echo "================================================================================"
	@echo "Building Controls Simulator" 
	@echo "make commands"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
