FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04@sha256:ac55d124da4882b497f732d8dfd9a702d5447a5f29d08d56da6f64f0a1eb34bc

ARG DEBIAN_FRONTEND=noninteractive
ARG UPSTREAM_COMMIT=7f1655ff1295c9a6dcf8d24f6410a036cd7e3497

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/sprkd-replication

COPY requirements-replication.lock ./
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pip==26.0.1 \
    && /opt/venv/bin/pip install --no-cache-dir --require-hashes \
        -r requirements-replication.lock

# Fetch only the package source at the frozen paper-linked commit. The 391 MB
# image dataset is mounted at runtime so it is not silently duplicated in the
# container image.
RUN git clone --filter=blob:none --no-checkout \
        https://github.com/thetechdude124/SADDLE-POINT-RECRUITMENT-FOR-KNOWLEDGE-DISTILLATION.git \
        /opt/upstream \
    && git -C /opt/upstream sparse-checkout init --cone \
    && git -C /opt/upstream sparse-checkout set sprkd \
    && git -C /opt/upstream checkout "$UPSTREAM_COMMIT" \
    && test "$(git -C /opt/upstream rev-parse HEAD)" = "$UPSTREAM_COMMIT"

COPY scripts/*.py /opt/sprkd-replication/scripts/
ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONPATH=/opt/upstream:/opt/sprkd-replication/scripts

ENTRYPOINT ["python", "/opt/sprkd-replication/scripts/run_trial.py"]
