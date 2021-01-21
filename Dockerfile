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
ENV PYENV_ROOT="${HOME}/.pyenv"
ENV PATH="${HOME}/.local/bin:${PYENV_ROOT}/shims:${PYENV_ROOT}/bin:${PATH}"
ENV VENV_NAME="${USER_NAME}_venv"

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
    p7zip-full \
    && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install nodejs and npm (for plotly)
# install pyenv https://github.com/pyenv/pyenv-installer
# note: pyenv.run is not accessible to all networks, use github url
# install FMI library
# install FMUComplianceChecker
# install EnergyPlusToFMU
# download and extract PyFMI release
# note: PyFMI 2.7.4 is latest release that doesnt require Assimulo which is unnecessary
# because we dont use builtin PyFMI ODE simulation capabilities
RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo bash - \
    && sudo apt-get update && sudo apt-get install -y nodejs \
    && curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash \
    && pyenv update && pyenv install 3.8.6 \
    && mkdir "${LIB_DIR}" && mkdir "${EXT_DIR}" \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/modelon-community/fmi-library/archive/2.2.3.zip" \
    && unzip "2.2.3.zip" && mv "fmi-library-2.2.3" "FMIL" \
    && rm -rf "2.2.3.zip" \
    && cd "FMIL" \
    && mkdir build-fmil; cd build-fmil \
    && cmake -DFMILIB_INSTALL_PREFIX=./ ../ \
    && make install test \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/modelica-tools/FMUComplianceChecker/releases/download/2.0.4/FMUChecker-2.0.4-linux64.zip" \
    && unzip "FMUChecker-2.0.4-linux64.zip" \
    && rm "FMUChecker-2.0.4-linux64.zip" \
    && mv "FMUChecker-2.0.4-linux64" "FMUComplianceChecker" \
    && mkdir "fmu" \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/lbl-srg/EnergyPlusToFMU/archive/v3.0.0.zip" \
    && unzip "v3.0.0.zip" && rm "v3.0.0.zip" \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/modelon-community/PyFMI/archive/PyFMI-2.7.4.tar.gz" \
    && tar -xzf "PyFMI-2.7.4.tar.gz" \
    && mv "${EXT_DIR}/PyFMI-PyFMI-2.7.4" "${EXT_DIR}/PyFMI" \
    && rm -rf "${EXT_DIR}/PyFMI-PyFMI-2.7.4" "PyFMI-2.7.4.tar.gz" \
    && mkdir "${PACKAGE_DIR}" \
    && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# copying will cause rebuild at minimum to start from here
# use .dockerignore to add files to docker image
COPY ./ "${PACKAGE_DIR}"

# copied directory will not have user ownership by default
# install energyplus versions desired in `scripts/setup/install_ep.sh`
# install python dev environment
# copy .bashrc file to user home for use on startup. This can be further configured by user.
RUN sudo chown -R "${USER_NAME}" "${PACKAGE_DIR}" \
    && cd "${PACKAGE_DIR}" \
    && mv ".vscode" "${LIB_DIR}/.vscode"
    && sudo chmod +x "./scripts/setup/install_ep.sh" \
    && sudo ./scripts/setup/install_ep.sh "${ENERGYPLUS_INSTALL_DIR}" \
    && cd "${PACKAGE_DIR}" \
    && ${PYENV_ROOT}/versions/3.8.6/bin/python3.8 -m venv "${LIB_DIR}/${VENV_NAME}" \
    && . "${LIB_DIR}/${VENV_NAME}/bin/activate" \
    && pip install --no-cache-dir --upgrade setuptools pip \
    && pip install --no-cache-dir -r "requirements.txt" \
    # && pip install --no-cache-dir -r "requirements_unfixed.txt" \
    && pip install --editable . \
    && cd "${EXT_DIR}/PyFMI" \
    && python "setup.py" install --fmil-home="${FMIL_HOME}" \
    && cd "${EXT_DIR}" \
    && wget "https://github.com/RJT1990/pyflux/archive/0.4.15.zip" \
    && unzip "0.4.15.zip" && rm "0.4.15.zip" \
    && cd "pyflux-0.4.15" \
    && pip install --no-cache-dir .

# install jupyter lab extensions for plotly
# if jupyter lab build fails with webpack optimization, set --minimize=False
RUN cd "${PACKAGE_DIR}" \
    && . "${LIB_DIR}/${VENV_NAME}/bin/activate" \
    && export NODE_OPTIONS="--max-old-space-size=8192" \
    && jupyter labextension install @jupyter-widgets/jupyterlab-manager@2 --no-build \
    && jupyter labextension install jupyterlab-plotly --no-build \
    && jupyter labextension install plotlywidget@1.5.0 --no-build \
    && jupyter lab build --dev-build=False --minimize=True \
    && unset NODE_OPTIONS \
    && cp "${PACKAGE_DIR}/scripts/setup/.bashrc" "$HOME/.bashrc" \
    && chmod +x "${PACKAGE_DIR}/scripts/setup/jupyter_lab_bkgrnd.sh"

WORKDIR "${PACKAGE_DIR}"
