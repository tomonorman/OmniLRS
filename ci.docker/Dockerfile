ARG BASE_IMAGE=omnilrs-base:latest
FROM ${BASE_IMAGE}

WORKDIR /workspace/omnilrs

# Yamcs mission control (ground segment)
RUN apt-get update && apt-get install -q -y --no-install-recommends \
    openjdk-17-jdk-headless \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/OmniLRS/yamcs-mission-control-pragyaan.git /workspace/yamcs-mission-control-pragyaan \
    && cd /workspace/yamcs-mission-control-pragyaan \
    && python3 -m venv .venv/workshop \
    && .venv/workshop/bin/pip install --no-cache-dir -r requirements.txt \
    # Pre-fetch maven + server deps
    && cd yamcs-server \
    && ./mvnw -B -q -DskipTests package

COPY . .

# Fast revalidation: no-op if the manifests match the base image,
RUN pixi install --all

# Run tests, comment as appropiate for artefacts / directly.
#CMD ["pixi", "run", "test-ros2"]
CMD artefacts run $ARTEFACTS_JOB_NAME
