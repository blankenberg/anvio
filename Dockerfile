FROM ubuntu:xenial

ENV ANVIO_VERSION 5.2

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update
RUN apt-get install locales
RUN locale-gen en_US.UTF-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'

RUN apt-get install -y --no-install-recommends \
        build-essential \
        gsl-bin \
        hmmer \
        libgsl-dbg \
        libgsl-dev \
        libgsl2 \
        python3 \
        python3-pip \
        python3-dev \
        python3-numpy \
        python3-scipy \
        sqlite3 \
        wget \
        automake \
        libboost-all-dev \
        bsdmainutils \
        libblas-dev \
        liblapack-dev \
        libatlas-base-dev \
        gfortran \
        libzeep-dev \
        zlib1g-dev \
        libhdf5-serial-dev \
        libhdf5-dev \
        mcl \
        ncbi-blast+ \
        muscle \
    && mkdir -p /tmp/build \
    && wget https://github.com/bbuchfink/diamond/releases/download/v0.8.38/diamond-linux64.tar.gz -O /tmp/build/diamond-linux64.tar.gz \
    && tar -zxvf /tmp/build/diamond-linux64.tar.gz -C /tmp/build/ \
    && cp /tmp/build/diamond /usr/bin/ \
    && wget https://github.com/hyattpd/Prodigal/archive/v2.6.3.tar.gz -O /tmp/build/v2.6.3.tar.gz \
    && tar -zxvf //tmp/build/v2.6.3.tar.gz -C /tmp/build/ \
    && make -C /tmp/build/Prodigal-2.6.3/ \
    && cp /tmp/build/Prodigal-2.6.3/prodigal /usr/bin/ \
    && wget https://github.com/cmbi/xssp/archive/3.0.1.tar.gz -O /tmp/build/3.0.1.tar.gz \
    && tar -zxvf /tmp/build/3.0.1.tar.gz -C /tmp/build/ \
    && cd /tmp/build/xssp-3.0.1/ \
    && ./autogen.sh && ./configure  && make && make install && cd - \
    && wget https://github.com/refresh-bio/FAMSA/releases/download/v1.2.1/famsa-1.2.1-linux -O /usr/bin/famsa \
    && chmod +x /usr/bin/famsa \
    && wget http://www.microbesonline.org/fasttree/FastTree -O /usr/local/bin/FastTree \
    && chmod +x /usr/local/bin/FastTree \
    && pip3 install setuptools==35.0.1 \
    && pip3 install \
        cython==0.28.5 \
        bottle==0.12.13 \
        pysam==0.15.1 \
        ete3==3.1.1 \
        scikit-learn==0.19.2 \
        django==2.0.2 \
        h5py==2.8.0 \
        cherrypy==8.9.1 \
        requests==2.19.1 \
        psutil==5.4.3 \
        mistune==0.7.4 \
        six==1.11.0 \
        pandas==0.23.1 \
        matplotlib==2.2.3 \
        pyani==0.2.7 \
        statsmodels==0.9.0 \
        snakemake==5.2.4 \
    && pip3 install --upgrade numpy==1.15.1 \
    && pip3 install --no-deps anvio==$ANVIO_VERSION \
    && apt-get remove -y \
        binutils \
        build-essential \
        g++ \
        g++-4.8 \
        gcc \
        gcc-4.8 \
        make \
        patch \
    && apt-get -y autoremove \
    && apt-get -y autoclean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/*

ADD ./run_anvio_GIE.sh /

RUN echo "export PS1=\"\[\e[0m\e[47m\e[1;30m\] :: anvi'o :: \[\e[0m\e[0m \[\e[1;34m\]\]\w\[\e[m\] \[\e[1;32m\]>>>\[\e[m\] \[\e[0m\]\"" >> /root/.bashrc

#CMD /bin/bash -l

ENTRYPOINT ["/run_anvio_GIE.sh"]

EXPOSE 80
