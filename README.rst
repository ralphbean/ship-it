ship-it
=======

A curses-based, fedmsg-aware heads up display for Fedora package maintainers.

The purpose of this tool is to automate the tasks that annoy me:

- I have X packages not monitored by anitya.. I don't want to go track down and
  find them all.  I want a tool that adds all the new one with one keystroke.
- and then forces a recheck.
- and then lists all bugs where things are out of date.
- then kicks off scratch builds for all those.
- then builds for rawhide any that are fine.
- and then merges that stuff into a release branch, builds it, creates updates, associates bugs and closes them, etc.
- etc...

I've done it by hand too many times.
