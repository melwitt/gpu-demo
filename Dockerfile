FROM docker.io/fedora:27


LABEL ios.k8s.display-name="deepspeech" \
    maintainer="Keith Tenzer <ktenzer@redhat.com>"

RUN dnf groupinstall -y 'C Development Tools and Libraries'
RUN dnf install -y python2 \
    python2-devel \
    git \
    wget \
    swig \
    langpacks-de \
    langpacks-es \
    langpacks-fr \
    langpacks-pl

RUN mkdir /deepspeech

RUN pip2 install 'deepspeech==0.3.0' \
    jamspell \
    webrtcvad \
    requests \
    certifi \
    urllib3 \
    idna \
    chardet

RUN cd /deepspeech && \
    git clone https://github.com/BoseCorp/py-googletrans.git && \
    cd /deepspeech/py-googletrans && \
    python2 /deepspeech/py-googletrans/setup.py install

RUN rm -rf /deepspeech/py-googletrans

RUN wget https://github.com/mozilla/DeepSpeech/releases/download/v0.3.0/deepspeech-0.3.0-models.tar.gz -P /deepspeech && \
    tar xzf /deepspeech/deepspeech-0.3.0-models.tar.gz -C /deepspeech

RUN rm -f /deepspeech/deepspeech-0.3.0-models.tar

RUN git clone https://github.com/ktenzer/gpu-demo.git /deepspeech/gpu-demo

COPY demo.wav /deepspeech

RUN chown -R 1001:0 /deepspeech && \
    chown -R 1001:0 $HOME

RUN echo "1.0" > /etc/imageversion

USER 1001

CMD ["-c", "--", "while true; do sleep 30; done;"]
ENTRYPOINT ["/bin/bash"]
