A Text UI Framework for Python

# Troubleshooting

## Cygwin

Most of these configurations have to be done in the settings for the
cygwin terminal emulator. Settings can be found by right-clicking the
titlebar, and choosing options from the applications context menu.


### Unicode characters

Emacs integration parses return values from emacs function calls, and
translates these to corresponding Python data types, if possible. This
is used, e.g., when declaring emacs functions in Python to fetch the
documentation for the function.

Go to Options -> Text and select a character encoding. Emacsclient on
Emacs/W32 outputs characters encoded in CP1252.


### Cygwin and Colors

If you get a message "Can not set colors." when loading a theme or
redefining colors, this means that your terminal is identified by
ncurses as a terminal which does not allow this.  In order to have
support for redefining colors, you need to enable this in your
terminal.  Go to Options -> Terminal and set type to VT256.
