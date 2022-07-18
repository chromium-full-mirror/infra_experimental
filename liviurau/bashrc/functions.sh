
function ledb() {
    led get-build "$@" | led edit-recipe-bundle | led launch
}

function ledb_py3() {
    led get-build "$@" | led edit-recipe-bundle | led edit -experiment luci.recipes.use_python3=true | led launch
}


function ledbb() {
    led get-build $1 | jq '.buildbucket.bbagent_args.build.infra.swarming.task_dimensions += [{key:"id", value:"'$2'", expiration:"0s"}]' | led launch
}

function bdiff() {
    git diff --name-only --diff-filter=d | xargs bat --diff
}

function local_git_google() {
    git config --local user.email "liviurau@google.com" && git commit --amend --no-edit --author="Liviu Rau <liviurau@google.com>"
}

function local_git_chromium() {
    git config --local user.email "liviurau@chromium.org" && git commit --amend --no-edit --author="Liviu Rau <liviurau@chromium.org>"
}

function screenshots_since() {
    bb ls -predicate \
    '{"builder":{"project":"devtools-internal","bucket":"try","builder":"devtools_screenshot_linux_rel"},"createTime":{"startTime": "'$1'T00:00:00.0Z"}}' \
    -json
}

function screenshots_authors() {
    screenshots_since $1 | jq -r .createdBy | cut -d: -f2 | sort | uniq
}

function screenshots_cls() {
    screenshots_since $1 | jq -r .input.gerritChanges[0].change | sort | uniq | wc -l
}
