# mprisctl

A command line media player controlling utility.

## What is it?

`mprisctl` is a command line utility that controls media players that implement [MPRIS D-Bus Interface](https://specifications.freedesktop.org/mpris-spec/2.2/). Not only this utility can help binding built-in media control keys to actual player actions, but also it is capable of displaying information about the current song. This is particularly useful when you want to customize your status line viewers such as [Polybar](https://github.com/polybar/polybar) or [Lemonbar](https://github.com/LemonBoy/bar).

## How to get it?

Clone this repository and `cd` into the repository.

```sh
git clone https://github.com/RangHo/mprisctl
cd mprisctl
```

Install it as a PIP package.

```sh
pip install .
```

Now, you should be able to use this utility by typing `mprisctl` in your command line!

