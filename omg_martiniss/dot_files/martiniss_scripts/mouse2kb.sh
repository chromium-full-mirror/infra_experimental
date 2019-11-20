#!/bin/bash
# set XKB layout
setxkbmap -layout us
# turn on mousekeys
xkbset m
# stop mousekeys expiring after a timeout
xkbset exp =m
# map keysym to other keysym
#xmodmap -e "keysym Menu = Pointer_Button2"
# this also works
# h
 #xmodmap -e "keycode 43 = Pointer_Button2"
# z
 #xmodmap -e "keycode 52 = Pointer_Button1"
# a
 #xmodmap -e "keycode 38 = Pointer_Button3"
