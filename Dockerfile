FROM frappe/erpnext:version-16 AS base
FROM base AS builder
USER root
RUN apt-get update && \
  apt-get install -y git ca-certificates && \
  rm -rf /var/lib/apt/lists/*
USER frappe
RUN echo '{"socketio_port": 9000}' > /home/frappe/frappe-bench/sites/common_site_config.json

RUN yarn config set registry https://registry.npmjs.org \
  && yarn config set network-timeout 600000 \
  && yarn config set prefer-offline true \
  && yarn config set retry 5

ENV GIT_TERMINAL_PROMPT=0


RUN bench get-app hrms --branch version-16 
RUN --mount=type=secret,id=gh_token,mode=0444 \
  export GH_TOKEN=$(cat /run/secrets/gh_token) && \
  bench get-app kya_hr "https://x-access-token:${GH_TOKEN}@github.com/KYA-TechTeam/kya_hr.git" --branch main 

RUN bench build \ 
  --app hrms \
  --app kya_hr \
  --force \
  && echo '{}' > /home/frappe/frappe-bench/sites/common_site_config.json