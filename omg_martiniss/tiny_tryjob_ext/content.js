let seenNotice = false;
function replaceClick() {
    chain = [
        "gr-app-element",
        "gr-change-view",
        "gr-change-actions",
        "section#secondaryActions"
    ]

    var needle = document.querySelector("gr-app");
    for (const item in chain) {
        if (!needle) {
            return;
        }
        needle = needle.shadowRoot.querySelector(chain[item]);
    }
    let found = 0;
    for (const child in needle.children) {
        let c = needle.children[child];
        if (!c.textContent) {
            continue;
        }
        let content = c.textContent.trim();
        if (content == "[FIND OWNERS]") {
            found ++;
        }
        if (content == "Code-Review+1") {
            found ++;
        }
    }
    if (found < 2) {
        return false;
    }

    for (const child in needle.children) {
        let c = needle.children[child];
        if (!c.textContent) {
            continue;
        }
        if (c.textContent.trim() == "CQ Dry Run") {
            let p = document.createElement("span")
            p.style.position = 'absolute';
            let size = c.getBoundingClientRect();
            p.style.width = size.width + "px";
            p.style.height = size.height + "px";
            p.style.zIndex = 10000;
            p.style.cursor = 'pointer';
            p.onclick = function(e) {
                if (seenNotice) {
                    return;
                }
                e.preventDefault();
                e.stopImmediatePropagation();
                let div = makeModal(() => {
                    seenNotice = true;
                    c.click();
                })
                document.querySelector("body").appendChild(div);
            }
            c.shadowRoot.insertBefore(p, c.shadowRoot.children[1]);
            return true;
        }
    }
}

function makeModal(callback) {
    let div = document.createElement("div");
    div.style.position = 'fixed';
    div.style.left = "0";
    div.style.right = "0";
    div.style.top = "0";
    div.style.height = "100%";
    div.style.width = "100%";
    div.style.zIndex = 100;
    div.style.background = "rgba(128, 128, 128, 0.5)";
    div.style.display = "flex";
    div.style.alignItems = "center";
    div.style.justifyContent = "center";

    let subDiv = document.createElement("div");
    subDiv.style.borderStyle = "normal";
    subDiv.style.border = "1px";
    subDiv.style.backgroundColor = "white";
    subDiv.style.maxWidth = "40%";
    div.appendChild(subDiv);

    let span = document.createElement("span");
    span.style.fontSize = "14px";
    span.style.font = "Roboto";
    span.style.padding = "2px";
    let p = document.createElement("p");
    p.style.paddingLeft = "10px";
    p.innerHTML = "Hi there! You decided to dogfood the tiny tryjob utility, and installed an extension as a result.<br>If you are testing your CL while developing it, please try using the tiny tryjob command, as detailed <a href=\"https://chromium.googlesource.com/chromium/src/tools/mb/+/HEAD/docs/user_guide.md#mb-try\">here</a> and click \"No\".<br>If you do want to actually run a CQ Dry Run, click \"Yes\", and one will be triggered.";
    span.appendChild(p);
    subDiv.appendChild(span);

    let buttonDiv = document.createElement("div");
    buttonDiv.style.display = "flex";
    buttonDiv.style.justifyContent = "space-evenly";
    subDiv.appendChild(buttonDiv);

    let button = document.createElement("button");
    button.textContent = "YES";
    button.style.marginBottom = "5px";
    button.style.fontWeight = "24"
    button.onclick = (e) => {
        div.remove();
        callback();
    }
    buttonDiv.appendChild(button);

    button = document.createElement("button");
    button.textContent = "NO";
    button.style.marginBottom = "5px";
    button.onclick = (e) => {
        div.remove();
    }
    buttonDiv.appendChild(button);

    return div;
}

const timeout = 1000;

function ensureReplaced() {
    if (replaceClick()) {
        return;
    }
    setTimeout(ensureReplaced, timeout);
}
setTimeout(ensureReplaced, timeout);