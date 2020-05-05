FROM ubuntu:20.04

MAINTAINER Tom Stesco <tom.s@ecobee.com>

# env vars
# Use C.UTF-8 locale to avoid issues with ASCII encoding
ENV LANG="C.UTF-8"
ENV LC_ALL="C.UTF-8"
ENV DEBIAN_FRONTEND="noninteractive"
ENV USER_NAME="bcs"
ENV IS_DOCKER_ENV="true"
ENV PACKAGE_NAME="building-control-simulator"
ENV PYENV_SHELL="bash"

# dependent env vars
ENV HOME="/home/${USER_NAME}"
ENV LIB_DIR="${HOME}/lib"
ENV EXT_DIR="${LIB_DIR}/external"
ENV ENERGYPLUS_INSTALL_DIR="/usr/local"
ENV FMIL_HOME="${EXT_DIR}/FMIL/build-fmil" 
ENV PACKAGE_DIR="${LIB_DIR}/${PACKAGE_NAME}"
ENV PATH="${HOME}/.local/bin:${HOME}/pyenv/shims:${HOME}/pyenv/bin:${PATH}"
ENV PYENV_ROOT="${HOME}/pyenv"

RUN apt-get update && apt-get install -y --no-install-recommends sudo

# create application user
RUN groupadd --gid 3434 "${USER_NAME}" \
  && useradd --uid 3434 --gid "${USER_NAME}" --shell /bin/bash --create-home "${USER_NAME}" \
  && echo 'bcs ALL=NOPASSWD: ALL' >> "/etc/sudoers.d/50-${USER_NAME}" \
  && echo 'Defaults    env_keep += "DEBIAN_FRONTEND"' >> /etc/sudoers.d/env_keep

# give user ownership and rwx of $HOME and rwx default EnergyPlus install location
RUN chown -R "${USER_NAME}":"${USER_NAME}" "${HOME}" \
    && chmod -R 775 "${HOME}" "/usr/local"

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
    # libssl1.0-dev \
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
    && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# install nodejs and npm (for plotly)
RUN curl -sL https://deb.nodesource.com/setup_12.x | sudo bash - \
    && sudo apt-get install -y nodejs

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

# download and extract PyFMI release
RUN cd "${EXT_DIR}" \
    && wget "https://github.com/modelon-community/PyFMI/archive/PyFMI-2.7.tar.gz" \
    && tar -xzf "PyFMI-2.7.tar.gz" \
    && mv "${EXT_DIR}/PyFMI-PyFMI-2.7" "${EXT_DIR}/PyFMI" \
    && rm -rf "${EXT_DIR}/PyFMI-PyFMI-2.7"

RUN mkdir "${PACKAGE_DIR}"

COPY ./ "${PACKAGE_DIR}/" 

RUN cd "${PACKAGE_DIR}" \
    && sudo chmod +x "./scripts/setup/install_ep.sh" \
    && ./scripts/setup/install_ep.sh

# install python dev environment
RUN cd "${PACKAGE_DIR}" \
    && pipenv install --dev --skip-lock

RUN cd "${EXT_DIR}/PyFMI" \
    && . ${HOME}/.local/share/virtualenvs/$( ls "${HOME}/.local/share/virtualenvs/" | grep "${PACKAGE_NAME}" )/bin/activate \
    && python "setup.py" install --fmil-home="${FMIL_HOME}"

ENV PATH="${HOME}/.local/bin:/usr/local/bin:${HOME}/pyenv/shims:${HOME}/pyenv/bin:${PATH}"
RUN cd "${PACKAGE_DIR}" \
    && . ${HOME}/.local/share/virtualenvs/$( ls "${HOME}/.local/share/virtualenvs/" | grep "${PACKAGE_NAME}" )/bin/activate \
    && pip install -e ./ --log "${PACKAGE_DIR}/piplog.txt" \
    && export NODE_OPTIONS=--max-old-space-size=4096 \
    && jupyter labextension install @jupyter-widgets/jupyterlab-manager@2 --no-build \
    && jupyter labextension install jupyterlab-plotly --no-build \
    && jupyter labextension install plotlywidget@1.5.0 --no-build \
    && jupyter lab build \
    && unset NODE_OPTIONS

# copy .bashrc file to user home for use on startup. This can be further configured by user.
RUN cp "${PACKAGE_DIR}/scripts/setup/.bashrc" "$HOME/.bashrc" \
    && chmod +x "${PACKAGE_DIR}/scripts/setup/jupyter_lab_bkgrnd.sh"

WORKDIR "${PACKAGE_DIR}"
