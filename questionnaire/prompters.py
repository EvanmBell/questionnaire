"""All prompters registered in this module must have a function signature
of (prompt="", **kwargs), and must return an (answer, back) tuple, even if
a back event doesn't occur. If the value for back is an int, the
questionnaire will go back that number of questions.

Extending questionnaire is as simple writing your own prompter and passing
it to `add_question`.
"""
import sys
import curses
import os
from contextlib import contextmanager

from pick import Picker


prompters = {}


def register(key="function"):
    """Add decorated functions to prompters dict.
    """
    def decorate(func):
        prompters[key] = func
        return func
    return decorate


@register(key="single")
def single(prompt="", **kwargs):
    """Instantiates a picker, registers custom handlers for going back,
    and starts the picker.
    """
    def go_back(picker):
        return None, -1
    options = kwargs.get('options', [])

    picker = Picker(options, title=prompt, indicator='=>')
    picker.register_custom_handler(ord('h'), go_back)
    picker.register_custom_handler(curses.KEY_LEFT, go_back)
    with stdout_redirected(sys.stderr):
        option, i = picker.start()
        if i < 0:  # user went back
            return option, 1
        return option, None


@register(key="multiple")
def multiple(prompt="", **kwargs):
    """Calls `pick` in a while loop to allow user to pick multiple
    options. Returns a list of chosen options.
    """
    ALL = kwargs.get('all', 'all')
    DONE = kwargs.get('done', 'done...')
    options = kwargs.get('options', [])
    options = [ALL] + options + [DONE] if ALL else options + [DONE]
    options_ = []
    while True:
        option, i = single('{}{}'.format(prompt, options_), options=options)
        if type(i) is int:  # user went back
            return (options_, 0) if options_ else (options_, 1)
        if ALL and option == ALL:
            return ([ALL], None)
        if option == DONE:
            return (options_, None)
        options_.append(option)
        options.remove(option)


@register(key="raw")
def raw(prompt="", **kwargs):
    """Calls input to allow user to input an arbitrary string. User can go
    back by entering the `go_back` string. Works in both Python 2 and 3.
    """
    go_back = kwargs.get('go_back', '<')
    type_ = kwargs.get('type', str)
    with stdout_redirected(sys.stderr):
        while True:
            try:
                if sys.version_info < (3, 0):
                    answer = raw_input(prompt)
                else:
                    answer = input(prompt)
                return (answer, 1) if answer == go_back else (type_(answer), None)
            except ValueError:
                print("\n`{}` is not a valid `{}`\n".format(answer, type_))


@contextmanager
def stdout_redirected(to):
    """Lifted from: https://stackoverflow.com/questions/4675728/redirect-stdout-to-a-file-in-python

    This is the only way I've found to redirect stdout with curses. This way the
    output from questionnaire can be piped to another program, without piping
    what's written to the terminal by the prompters.
    """
    stdout = sys.stdout

    stdout_fd = fileno(stdout)
    # copy stdout_fd before it is overwritten
    with os.fdopen(os.dup(stdout_fd), 'wb') as copied:
        stdout.flush()  # flush library buffers that dup2 knows nothing about
        try:
            os.dup2(fileno(to), stdout_fd)  # $ exec >&to
        except ValueError:  # filename
            with open(to, 'wb') as to_file:
                os.dup2(to_file.fileno(), stdout_fd)  # $ exec > to
        try:
            yield stdout  # allow code to be run with the redirected stdout
        finally:
            # restore stdout to its previous value
            stdout.flush()
            os.dup2(copied.fileno(), stdout_fd)


def fileno(file_or_fd):
    fd = getattr(file_or_fd, 'fileno', lambda: file_or_fd)()
    if not isinstance(fd, int):
        raise ValueError("Expected a file (`.fileno()`) or a file descriptor")
    return fd
