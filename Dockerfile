FROM ubuntu:20.04

MAINTAINER Tom Stesco <tom.s@ecobee.com>

# env vars
# Use C.UTF-8 locale to avoid issues with ASCII encoding
ENV LANG="C.UTF-8"
ENV LC_ALL="C.UTF-8"
ENV USER_NAME="bcs"
ENV IS_DOCKER_ENV="true"
ENV PACKAGE_NAME="building-controls-simulator"
ENV PYENV_SHELL="bash"

# dependent env vars
ENV HOME="/home/${USER_NAME}"
ENV LIB_DIR="${HOME}/lib"
ENV EXT_DIR="${LIB_DIR}/external"
ENV ENERGYPLUS_INSTALL_DIR="${EXT_DIR}/EnergyPlus"
ENV FMIL_HOME="${EXT_DIR}/FMIL/build-fmil" 
ENV PACKAGE_DIR="${LIB_DIR}/${PACKAGE_NAME}"
ENV PATH="${HOME}/.local/bin:${HOME}/pyenv/shims:${HOME}/pyenv/bin:${PATH}"
ENV PYENV_ROOT="${HOME}/pyenv"

# set build noninteractive
ARG DEBIAN_FRONTEND=noninteractive

# create application user and give user ownership of $HOME
RUN apt-get update && apt-get install -y --no-install-recommends sudo \
    && adduser "${USER_NAME}" --shell /bin/bash --disabled-password --gecos "" \
    && adduser "${USER_NAME}" sudo \
    && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
    && echo 'Defaults    env_keep += "DEBIAN_FRONTEND"' >> "/etc/sudoers.d/env_keep" \
    && chown -R "${USER_NAME}" "${HOME}"

USER "${USER_NAME}"

# install core system libraries
RUN sudo apt-get update && sudo apt-get upgrade -y \
    && sudo apt-get install -y --no-install-recommends \
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
    liblzma-dev \
    libssl-dev \
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
    p7zip-full

# install nodejs and npm (for plotly)
# install pip
# install pyenv https://github.com/pyenv/pyenv-installer
# install pipenv
# install FMI library
# install FMUComplianceChecker
# install EnergyPlusToFMU
# download and extract PyFMI release
# clean up
RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo bash - \
    && sudo apt-get install -y nodejs \
    && curl --silent https://bootstrap.pypa.io/get-pip.py | python3 \
    && curl https://pyenv.run | bash \
    && pyenv update && pyenv install 3.7.6 \
    && pip3 install pipenv \
    && mkdir "${LIB_DIR}" && mkdir "${EXT_DIR}" \
    && cd "${EXT_DIR}" \
    && wget https://github.com/modelon-community/fmi-library/archive/2.2.zip \
    && unzip 2.2.zip && mv fmi-library-2.2 FMIL \
    && rm -rf 2.2.zip \
    && cd FMIL \
    && mkdir build-fmil; cd build-fmil \
    && cmake -DFMILIB_INSTALL_PREFIX=./ ../ \
    && make install test \
    && cd "${EXT_DIR}" \
    && wget https://github.com/modelica-tools/FMUComplianceChecker/releases/download/2.0.4/FMUChecker-2.0.4-linux64.zip \
    && unzip FMUChecker-2.0.4-linux64.zip \
    && rm FMUChecker-2.0.4-linux64.zip \
    && mv FMUChecker-2.0.4-linux64 FMUComplianceChecker \
    && mkdir fmu \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/lbl-srg/EnergyPlusToFMU/archive/v3.0.0.zip" \
    && unzip v3.0.0.zip && rm v3.0.0.zip
    && cd "${EXT_DIR}" \
    && wget "https://github.com/modelon-community/PyFMI/archive/PyFMI-2.7.4.tar.gz" \
    && tar -xzf "PyFMI-2.7.4.tar.gz" \
    && mv "${EXT_DIR}/PyFMI-PyFMI-2.7.4" "${EXT_DIR}/PyFMI" \
    && rm -rf "${EXT_DIR}/PyFMI-PyFMI-2.7.4" "PyFMI-2.7.4.tar.gz" \
    && mkdir "${PACKAGE_DIR}" \
    && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# copying in a directory will cause rebuild at minimum to start from here
COPY ./ "${PACKAGE_DIR}" 

# copied directory will not have user ownership by default
# install energyplus versions desired in `scripts/setup/install_ep.sh`
# install python dev environment
# copy .bashrc file to user home for use on startup. This can be further configured by user.
RUN sudo chown -R "${USER_NAME}" "${PACKAGE_DIR}" \
    && cd "${PACKAGE_DIR}" \
    && sudo chmod +x "./scripts/setup/install_ep.sh" \
    && sudo ./scripts/setup/install_ep.sh "${ENERGYPLUS_INSTALL_DIR}" \
    && cd "${PACKAGE_DIR}" \
    && pipenv install --dev --skip-lock \
    && cd "${EXT_DIR}/PyFMI" \
    && . ${HOME}/.local/share/virtualenvs/$( ls "${HOME}/.local/share/virtualenvs/" | grep "${PACKAGE_NAME}" )/bin/activate \
    && python "setup.py" install --fmil-home="${FMIL_HOME}"

# install jupyter lab extensions for plotly
# if jupyter lab build fails with webpack optimization, set --minimize=False
RUN cd "${PACKAGE_DIR}" \
    && . ${HOME}/.local/share/virtualenvs/$( ls "${HOME}/.local/share/virtualenvs/" | grep "${PACKAGE_NAME}" )/bin/activate \
    && export NODE_OPTIONS=--max-old-space-size=8192 \
    && jupyter labextension install @jupyter-widgets/jupyterlab-manager@2 --no-build \
    && jupyter labextension install jupyterlab-plotly --no-build \
    && jupyter labextension install plotlywidget@1.5.0 --no-build \
    && jupyter lab build --dev-build=False --minimize=True \
    && unset NODE_OPTIONS \
    && cp "${PACKAGE_DIR}/scripts/setup/.bashrc" "$HOME/.bashrc" \
    && chmod +x "${PACKAGE_DIR}/scripts/setup/jupyter_lab_bkgrnd.sh"

WORKDIR "${PACKAGE_DIR}"
