FROM python:alpine

# deps
RUN apk add --no-cache bash git openssh

# not root
ARG UID
ARG USER
RUN adduser -u ${UID} -h /home/${USER} -s /bin/bash -D ${USER}
USER ${USER}

# this is where pip will install the executable
RUN echo "export PATH=/home/${USER}/.local/bin:$PATH" >> /home/${USER}/.bash_profile

# copy over the source and pip install it
RUN mkdir -p /home/${USER}/src/brightmd/reflex
COPY . /home/${USER}/src/brightmd/reflex/
WORKDIR /home/${USER}/src/brightmd/reflex
RUN pip install .

# purely personal choice
RUN echo "set editing-mode vi" >> /home/${USER}/.inputrc
