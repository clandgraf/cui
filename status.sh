find . src/* -maxdepth 0 -type d -exec sh -c '(cd {} && echo {}@`git rev-parse --abbrev-ref HEAD` && git status -s && echo)' \;
