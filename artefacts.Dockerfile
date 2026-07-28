FROM tomolnorman/omnilrs-ci-base:0.2.0

# Cloud runner hosts (Amazon Linux) inject two NVIDIA Vulkan ICD manifests
# (nvidia_icd.json + nvidia_icd.x86_64.json) for the same driver, making one
# GPU enumerate twice and crashing Kit in multi-GPU mode. Pin the loader to a
# single manifest. Ubuntu 22.04 ships Vulkan loader 1.3.204, which predates
# VK_DRIVER_FILES (added in 1.3.207) and only honors the legacy name, so set both.
ENV VK_DRIVER_FILES=/etc/vulkan/icd.d/nvidia_icd.json
ENV VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_icd.json

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
