FROM ubuntu:18.04

MAINTAINER Tom Stesco <tom.s@ecobee.com>

USER root

# user variables
ENV HOME="/root/home"
ENV PACKAGE_NAME="building-control-simulator"
ENV LIB_DIR="${HOME}/lib"
ENV EXT_DIR="${LIB_DIR}/external"
ENV FMIL_HOME="${EXT_DIR}/FMIL/build-fmil"
ENV PACKAGE_DIR="${LIB_DIR}/${PACKAGE_NAME}"
ENV ENERGYPLUS_INSTALL_DIR="/usr/local"

# fixed vars
WORKDIR "${HOME}"
# Use C.UTF-8 locale to avoid issues with ASCII encoding
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV IS_DOCKER_ENV="true"
ARG DEBIAN_FRONTEND="noninteractive"

ENV LANG="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    PATH="${HOME}/pyenv/shims:${HOME}/pyenv/bin:${PATH}" \
    PYENV_ROOT="${HOME}/pyenv" \
    PYENV_SHELL="bash"

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libbz2-dev \
    libffi-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl1.0-dev \
    liblzma-dev \
    # libssl-dev \
    llvm \
    make \
    cmake \
    netbase \
    pkg-config \
    tk-dev \
    wget \
    xz-utils \
    zlib1g-dev \
    unzip \
    python2.7 \
    python3-dev \
    python3-distutils \
    subversion \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install pip
RUN curl --silent https://bootstrap.pypa.io/get-pip.py | python3

## install pyenv https://github.com/pyenv/pyenv-installer
RUN curl https://pyenv.run | bash
RUN pyenv update && pyenv install 3.7.6

# install pipenv
RUN pip3 install pipenv

# install FMI library 
RUN mkdir "${LIB_DIR}" && mkdir "${EXT_DIR}" \
    && cd "${EXT_DIR}" \
    && wget https://github.com/modelon-community/fmi-library/archive/2.1.zip \
    && unzip 2.1.zip && mv fmi-library-2.1 FMIL \
    && rm -rf 2.1.zip \
    && cd FMIL \
    && mkdir build-fmil; cd build-fmil \
    && cmake -DFMILIB_INSTALL_PREFIX=./ ../ \
    && make install test

# install FMUComplianceChecker
RUN cd "${EXT_DIR}" \
    && wget https://github.com/modelica-tools/FMUComplianceChecker/releases/download/2.0.4/FMUChecker-2.0.4-linux64.zip \
    && unzip FMUChecker-2.0.4-linux64.zip \
    && rm FMUChecker-2.0.4-linux64.zip \
    && mv FMUChecker-2.0.4-linux64 FMUComplianceChecker \
    && mkdir fmu

# install EnergyPlusToFMU
RUN cd "${EXT_DIR}" \
    && git clone https://github.com/lbl-srg/EnergyPlusToFMU.git

RUN mkdir "${PACKAGE_DIR}"

COPY ./ "${PACKAGE_DIR}/" 

RUN cd "${PACKAGE_DIR}" \
    && chmod +x "./scripts/setup/install_ep.sh" \
    && ./scripts/setup/install_ep.sh

# install python dev environment
RUN cd "${PACKAGE_DIR}" \
    && pipenv install --dev --skip-lock \
    && git clone https://github.com/modelon-community/PyFMI.git "${EXT_DIR}/PyFMI" \
    && cd "${EXT_DIR}/PyFMI" \
    && . ${HOME}/.local/share/virtualenvs/$( ls "${HOME}/.local/share/virtualenvs/" | grep "${PACKAGE_NAME}" )/bin/activate \
    && python "setup.py" install --fmil-home="${FMIL_HOME}" \
    && cd "${PACKAGE_DIR}" \
    && pip install -e ./

# WARNING: FOR LOCAL HOSTING ONLY
# disables authentication for jupyter notebook server 
RUN mkdir "${HOME}/.jupyter" \
    && touch "${HOME}/.jupyter/jupyter_notebook_config.py" \
    && echo "c.NotebookApp.token = u''" >> "${HOME}/.jupyter/jupyter_notebook_config.py"

WORKDIR "${PACKAGE_DIR}"
