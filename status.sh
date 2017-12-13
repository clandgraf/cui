find . src/* -maxdepth 0 -type d -exec sh -c '(echo {} && cd {} && git status -s && echo)' \;
