# Pokémon Battle System

I thought I'd build a silly project.

I want to replicate a turn based monster fighting system, the back and forth, type based advantage, status effects, etc.

I'll probably go with gen 1 - 3, since that's what I played, and I'm not trying to accuratley simulate anything.

**THIS IS A FUNNY PROJECT. USE AT YOUR OWN RISK!!**

## Requirements

~~I need static pokemon data like base stats species id etc, move list, and a learn set per pokemon.~~

~~I'm still debating having static pokemon data in csv files, or in a sqlite db along with user instance data?~~

~~But I also need user instance pokemon data, which ones are in the party, what level, what moves, status effects, etc. Also need user data for a bag/inventory system eventually.~~

sqlite might be the easiest solution, idk if it's the best but it works.

For the actual battles, I want to implement strategy pattern in C, but I'm not sure how yet. Probably higher order functions and function pointers, oi. I'm still learning the nitty-gritty of C, so we'll see how this evolves.

- [x] Python scripts to fetch pokemon data
- [x] Stash Pokemon data into sqlite
- [ ] C sqlite setup?
  - [x] C db object setup
  - (need to think about creating everything in C?)
  - [x] How to query in C sqlite?
  - [ ] How to insert, update (upsert possible?) in C sqlite?
- [x] C sqlite library
- [ ] Load Pokedex
- [ ] Check for and load user save
  - [ ] If not save, prompt user to make one
  - [ ] Party selection menu
- [ ] ?What about Enemy and Their party?
- [ ] Strategy pattern in C, for the battle system
- [ ] C unit testing

Lol, slight detore accured. It took my like a week or 2 to scrap the pokeapi, create schemas and relationships that make sense for a simple cli app. Nothing fancy, and just the basics for a gen 1 pokemon battle.

No held items, no abilities, no stage advantages, none of that later gen stuff.

I then had to learn the BASICS of the C lanugage to do anything semi-productive, like query the pokedex from sqlite, and stash that into a struct list.

## Data

Using <https://pokeapi.co> and python to fetch and transform data from json to sqlite. Still in progress.

OpenAPI Schema file on github: <https://raw.githubusercontent.com/PokeAPI/pokeapi/master/openapi.yml>

## Gotchas

1. Add `-lsqlite3` to CC, to link sqlite3 library. Otherwise it won't compile.
2. Poke API data has so much damn data, it took me a week to write scripts to fetch the data and etl it into a sqlite db ... I'm tired bouss ...
