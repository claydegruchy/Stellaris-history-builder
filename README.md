# Stellaris-history-builder

## Whats it do?
- Extracts a Stellaris .sav file
- Converts the clausewitz gamestate file to a more easily readable json file
- Iterates over the file to do various things.
- It'll do more one day.

## How to use it:
viewSave.py -h
Basically, it can digest single or multiple saves, outputting a more human friendly .json file. It can also extract the keys from a save for easier interpretation.

## Todo:
- Implement front end with something like http://visjs.org/showcase/index.html, probably with some timeline scale stuff
- Add flask to host front end/deliver the data
- Add cross save deltas
- Add a data a export function
- Figure out why some star systems and planets have the max range number of `4294967295`.
- Include test to see what wars are underway, only better.
