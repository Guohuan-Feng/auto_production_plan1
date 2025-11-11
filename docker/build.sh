#!/bin/bash

. tools/functions.sh

image_version=$(bash tools/version.sh)

prod_image_registry="crxchinacdhprod.azurecr.cn"
dev_image_registry="crxchinacdhprod.azurecr.cn"
dev_mode="true"


current_branch=$(get_current_branch)
if [[ "$current_branch" == "main" || "${current_branch}" == "master" ]]; then
    image_registry=${prod_image_registry}
    dev_mode="false"
else
    image_registry=${dev_image_registry}
fi

export DEV=${dev_mode}

bash docker/build_image.sh ${image_registry} ${image_version} 
