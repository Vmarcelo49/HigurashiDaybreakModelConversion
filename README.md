# HigurashiDaybreakModelConversion

This project is a place to gather all the information i managed to find through testing and many hours of fruitless effort

## New info

Animations do export correctly from assimp, when we convert from .x to .gltf it works as expected because the animation timings are tied to the game framerate so we get lots of invalid animation durations.
I made some scripts to try to manually fix the timings, but it breaks a lot of stuff
