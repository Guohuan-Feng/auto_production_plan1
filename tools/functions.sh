#!/bin/bash

function get_current_branch() {
    current_branch=$(git branch --show-current)
    if [ -z "${current_branch}" ]; then
        current_branch=$(echo $BUILD_SOURCEBRANCH | awk -F/ '{print $NF}')
    fi
    echo ${current_branch}
}