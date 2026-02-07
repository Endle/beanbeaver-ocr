export BEANBEAVER_OCR_NAME=beanbeaver-receipt-ocr
set -xe
podman build --network=slirp4netns -t $BEANBEAVER_OCR_NAME .
podman run --replace --name BEANBEAVER_OCR_NAME --network=slirp4netns -p 8001:8000 $BEANBEAVER_OCR_NAME
# TODO should we use this 8001 port?

